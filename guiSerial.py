# -*- coding: utf-8 -*-

import io
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk
from collections import deque
import serial
import serial.tools.list_ports

import psutil

try:
    import pynvml
    pynvml.nvmlInit()
    HAS_NVML = True
except Exception:
    HAS_NVML = False

# ----------------------------------------------------
# [테스트 설정] 하드웨어 "OK" 응답 바이패스 (시뮬레이션 모드)
# ----------------------------------------------------
SIMULATION_MODE = True      # True: OK 수신 없이도 자동 진행
SIM_STEP_DELAY_MS = 60      # 각 G-code 라인 간 가상 진행 딜레이(ms)

MENU_NAMES = ["닭고기", "목살", "삼겹살", "양념"]
MENU_PRICE = 6000

# 조리 시간 상수: 총 조리 시간 12분 (720초), 뒤집기 타이밍 3분 (180초)
TOTAL_COOK_TIME = 12 * 60  
FLIP_TIME = 3 * 60        

# ----------------------------------------------------
# 1. 5단계 시퀀스 G-code 정의
# ----------------------------------------------------
def get_stage1_pick_gcode(menu_name):
    x_positions = {
        "닭고기": 2000,
        "목살": 2600,
        "삼겹살": 2700,
        "양념": 3000
    }
    x_val = x_positions.get(menu_name, 2000)
    
    return [
        "M103 P0 S2000 F2000",
        "M103 P1 S2000 F2000",
        "M103 P2 S2000 F2000",
        "M103 P3 S2000 F2000",
        "G28",
        f"G1 X{x_val}",
        "G38",
        "G1 X200",
        "G1 Z2000",
        "G1 Y2000",
        "G1 Z200",
        "G40",
        "M800 P4 S1",
        "M800 P5 S1",
        "G28 Z Y"
    ]

# 2단계 Unit Change 시퀀스
GCODE_UNIT1_CHANGE = [
    "M119",
    "G40"
]

GCODE_UNIT2_GRIP = [
    "M800 P0 S1",
    "G4 P2000"  # 2초 대기
]

GCODE_UNIT1_RELEASE = [
    "M800 P0 S0",
    "M800 P1 S0",
    "G4 P2000",  # 2초 대기
    "G28"
]

# 5단계 Finish 시퀀스
GCODE_UNIT2_FINISH = [
    "G28 Y",
    "G28 Z",
    "M800 P0 S1",
    "G1 Y1500 Z1500",
    "G28 X",
    "M800 P0 S0"
]

# ----------------------------------------------------
# 2. 전역 상태 및 슬롯 관리
# ----------------------------------------------------
NUM_SLOTS = 14  # Heatplate 1 (1~7), Heatplate 2 (8~14)

heat_units = {
    i: {
        "status": "idle",       # 'idle', 'reserved', 'cooking', 'flipped', 'finished'
        "plate_id": 1 if i <= 7 else 2,
        "start_time": 0,        # 총 조리 시작 시점
        "flip_time": 0,         # 뒷면으로 전환된 시점
        "front_duration": 0,    # 앞면 조리 완료 누적 시간
        "order": None, 
        "flipped": False
    }
    for i in range(1, NUM_SLOTS + 1)
}

menu_counter = [0, 0, 0, 0]
menu_buttons = []

table_orders = [{"count": 0, "amount": 0, "items": {name: 0 for name in MENU_NAMES}} for _ in range(5)]
table_buttons = []
table_order_detail_labels = []

dummy_buttons = []

portName = ['주문대기'] + ['-'] * NUM_SLOTS
initStat = ['세트대기'] + ['-'] * NUM_SLOTS
initBuffer = ['조리대기'] + ['-'] * NUM_SLOTS

LF2body = ['menuName'] + ['-'] * NUM_SLOTS
LF2body_value = ['now?'] + ['0'] * NUM_SLOTS

LF3cmos = ['deviceName']
LF3cmos_value = ['Status:??']
LF3cmos_entry = ['Command']

for i in range(1, NUM_SLOTS + 1):
    LF3cmos.append(f'COM{i}')
    LF3cmos_value.append(f'NOTIN{i}')
    LF3cmos_entry.append(f'Enter{i}')

c0Label, c1Label, c2Label, c3Label, c4Label, c5Label, c6Label, c7Entry = [], [], [], [], [], [], [], []

portlist = [None] * (NUM_SLOTS + 1)
port_names = [''] * (NUM_SLOTS + 1)
rx_buffers = [''] * (NUM_SLOTS + 1)

# 테스트 시뮬레이션을 위한 기본 슬롯 1, 2 매핑
board_slot_map = {1: 1, 2: 2}

slot_queues = {i: deque() for i in range(1, NUM_SLOTS + 1)}
slot_current_job = {i: None for i in range(1, NUM_SLOTS + 1)}
slot_dummy_buttons = []

cam_display_labels = []
analysis_buttons = [[], [], []]

is_running = True
orig_stdout = sys.stdout
orig_stderr = sys.stderr

active_orders = []
overflow_orders = []

is_unit1_busy = False
is_unit2_busy = False

current_sys_metrics = {
    "cpu": 0.0,
    "ram_pct": 0.0,
    "ram_used_gb": 0.0,
    "ram_total_gb": 0.0,
    "gpu_load": "N/A",
    "vram_used": "N/A"
}

# ----------------------------------------------------
# 3. 콘솔 출력 리다이렉터
# ----------------------------------------------------
class ConsoleRedirector:
    def __init__(self, text_widget, original_stream, tag='out', max_lines=60):
        self.text_widget = text_widget
        self.original_stream = original_stream
        self.tag = tag
        self.max_lines = max_lines

    def write(self, string):
        if self.original_stream:
            self.original_stream.write(string)
            self.original_stream.flush()

        if not string or not is_running:
            return

        def _append():
            if not is_running:
                return
            try:
                if not self.text_widget.winfo_exists():
                    return
                self.text_widget.configure(state='normal')
                self.text_widget.insert(tk.END, string, self.tag)
                
                num_lines = int(self.text_widget.index('end-1c').split('.')[0])
                if num_lines > self.max_lines:
                    self.text_widget.delete('1.0', f'{num_lines - self.max_lines}.0')

                self.text_widget.see(tk.END)
                self.text_widget.configure(state='disabled')
            except Exception:
                pass

        try:
            if is_running and self.text_widget.winfo_exists():
                self.text_widget.after(0, _append)
        except Exception:
            pass

    def flush(self):
        if self.original_stream:
            self.original_stream.flush()

# ----------------------------------------------------
# 4. 비동기 큐잉 G-code 엔진 (가상 OK 바이패스 지원)
# ----------------------------------------------------
def execute_gcode_sequence(slot_id, gcodes, on_done=None):
    if not (1 <= slot_id <= NUM_SLOTS):
        if on_done:
            on_done()
        return

    lines = [line.strip() for line in gcodes if line.strip() and not line.strip().startswith(";")]
    if not lines:
        if on_done:
            on_done()
        return

    job = {
        "lines": lines,
        "idx": 0,
        "waiting_ok": False,
        "on_done": on_done
    }
    slot_queues[slot_id].append(job)

    if slot_current_job[slot_id] is None:
        _process_next_job(slot_id)

def _process_next_job(slot_id):
    if not is_running:
        return
    if slot_queues[slot_id]:
        slot_current_job[slot_id] = slot_queues[slot_id].popleft()
        _send_job_line(slot_id)
    else:
        slot_current_job[slot_id] = None

def _send_job_line(slot_id):
    if not is_running:
        return
    job = slot_current_job[slot_id]
    if job is None:
        return

    if job["idx"] < len(job["lines"]):
        cmd = job["lines"][job["idx"]]
        
        if cmd.startswith("G4 P"):
            try:
                delay_ms = int(cmd.split("P")[1].strip())
                job["waiting_ok"] = True
                print(f"[DELAY Slot{slot_id}] {delay_ms}ms 대기")
                App.after(delay_ms, lambda: notify_slot_ok_received(slot_id))
                return
            except Exception:
                pass

        job["waiting_ok"] = True
        send_slot_command(slot_id, cmd)

        if SIMULATION_MODE:
            App.after(SIM_STEP_DELAY_MS, lambda: notify_slot_ok_received(slot_id))
    else:
        callback = job["on_done"]
        job["on_done"] = None
        job["waiting_ok"] = False
        if callback:
            callback()
        _process_next_job(slot_id)

def notify_slot_ok_received(slot_id):
    job = slot_current_job.get(slot_id)
    if job and job["waiting_ok"]:
        job["waiting_ok"] = False
        job["idx"] += 1
        if is_running and App.winfo_exists():
            App.after(5, lambda: _send_job_line(slot_id))

# ----------------------------------------------------
# 5. 시리얼 통신
# ----------------------------------------------------
def autoDetectAndConnect():
    global portlist, port_names, board_slot_map
    board_slot_map.clear()
    detected = [p.device for p in serial.tools.list_ports.comports()]
    print(f"[시스템] 감지된 직렬 포트: {detected}")

    for i in range(1, NUM_SLOTS + 1):
        if i - 1 < len(detected):
            dev_name = detected[i - 1]
            port_names[i] = dev_name
            c5Label[i].configure(text=f"{dev_name[:7]}")
            
            if portlist[i] is not None and portlist[i].is_open:
                continue
            try:
                portlist[i] = serial.Serial(dev_name, 115200, timeout=0.01)
                portlist[i].reset_input_buffer()
                c6Label[i].configure(text='Connected', foreground='green')
                print(f"[+] Slot {i} -> {dev_name} 연결 완료")
            except Exception as e:
                c6Label[i].configure(text='Error', foreground='orange')
                print(f"[!] {dev_name} 열기 오류: {e}")
        else:
            port_names[i] = ''
            c5Label[i].configure(text=f"Slot {i}")
            if portlist[i] is not None:
                try:
                    portlist[i].close()
                except Exception:
                    pass
                portlist[i] = None
            c6Label[i].configure(text='DC', foreground='gray')

    if 1 not in board_slot_map:
        board_slot_map[1] = 1
    if 2 not in board_slot_map:
        board_slot_map[2] = 2

def serialDisconnectAll():
    global portlist, board_slot_map
    board_slot_map.clear()
    board_slot_map[1] = 1
    board_slot_map[2] = 2
    print("[시스템] 모든 시리얼 연결 해제 (가상 매핑 유지)")
    for i in range(1, NUM_SLOTS + 1):
        if portlist[i] is not None:
            try:
                if portlist[i].is_open:
                    portlist[i].close()
            except Exception:
                pass
            portlist[i] = None
        if i < len(c6Label) and c6Label[i].winfo_exists():
            c6Label[i].configure(text="DC", foreground="black")

def serialTester():
    global portlist, rx_buffers, board_slot_map
    if not is_running:
        return

    try:
        for i in range(1, NUM_SLOTS + 1):
            ser = portlist[i]
            if ser is not None and ser.is_open:
                try:
                    waiting = ser.in_waiting
                    if waiting > 0:
                        chunk = ser.read(waiting).decode('utf-8', errors='ignore')
                        rx_buffers[i] += chunk
                        
                        if len(rx_buffers[i]) > 10000:
                            rx_buffers[i] = rx_buffers[i][-2000:]
                        
                        while '\n' in rx_buffers[i]:
                            line, rx_buffers[i] = rx_buffers[i].split('\n', 1)
                            line = line.strip()
                            if line:
                                print(f"[RX Slot{i}] {line}")
                                if c6Label[i].winfo_exists():
                                    c6Label[i].configure(text=line[:12], foreground="blue")
                                
                                clean_line = line.replace(" ", "").upper()

                                for b_id in [1, 2]:
                                    if f"READY_{b_id}" in clean_line or f"READY!{b_id}" in clean_line or f"UNIT{b_id}" in clean_line:
                                        board_slot_map[b_id] = i
                                        print(f"[동기화] STM32 Unit {b_id} -> Slot {i} 매핑 완료")

                                if not SIMULATION_MODE and (clean_line == "OK" or clean_line.endswith("OK")):
                                    notify_slot_ok_received(i)

                except Exception:
                    if c6Label[i].winfo_exists():
                        c6Label[i].configure(text="Error", foreground="red")
    finally:
        if is_running and App.winfo_exists():
            App.after(15, serialTester)

def send_slot_command(slot_id, gcode):
    if 1 <= slot_id < len(portlist):
        ser = portlist[slot_id]
        if ser is not None and ser.is_open:
            try:
                ser.write((gcode.strip() + "\r\n").encode("utf-8"))
                ser.flush()
                print(f"[TX Slot{slot_id}] {gcode}")
                return True
            except Exception as e:
                print(f"[!] Slot {slot_id} 송신 에러: {e}")
                return False
    print(f"[TX(Virtual) Slot{slot_id}] {gcode}")
    return False

def c7entrySender():
    for i in range(1, min(len(c7Entry), len(portlist))):
        widget = c7Entry[i]
        if isinstance(widget, tk.Entry):
            cmd = widget.get().strip()
            if cmd:
                send_slot_command(i, cmd)
                widget.delete(0, tk.END)

# ----------------------------------------------------
# 6. 5단계 파이프라인 및 조리대 가상 환경 버튼 동기화
# ----------------------------------------------------
STATUS_COLORS = {
    "대기": "gray",
    "1단계:Pick": "#d97706",
    "2단계:Change": "#9333ea",
    "3단계:CookPlace": "#2563eb",
    "4단계:조리(앞)": "#2563eb",
    "4단계:뒤집힘(뒷)": "#2563eb",
    "5단계:완성배출": "#16a34a",
    "-": "black"
}

def sync_order_queue_ui():
    for i in range(1, NUM_SLOTS + 1):
        idx = i - 1
        if idx < len(active_orders):
            item = active_orders[idx]
            name_text = f"T{item['table']} {item['name']}"
            stat_text = item['status']
            color = STATUS_COLORS.get(stat_text, "black")
        else:
            name_text = "-"
            stat_text = "-"
            color = "black"

        if i < len(c3Label) and c3Label[i].winfo_exists():
            c3Label[i].configure(text=name_text)
        if i < len(c4Label) and c4Label[i].winfo_exists():
            c4Label[i].configure(text=stat_text, fg=color)

def sync_heat_units_ui():
    now = time.time()
    for i in range(NUM_SLOTS):
        h_id = i + 1
        info = heat_units[h_id]
        btn = slot_dummy_buttons[i]
        if not btn.winfo_exists():
            continue
            
        st = info["status"]
        hp_no = info["plate_id"]
        
        if st == "idle":
            btn.configure(
                text=f"조리대 {h_id} (HP{hp_no})\n[비어있음]\n총 00:00\n앞 00:00 | 뒤 00:00",
                bg="#e2e8f0",
                fg="#64748b",
                font=("Arial", 7)
            )
        elif st in ["reserved", "cooking", "flipped"]:
            elapsed = int(now - info["start_time"]) if info["start_time"] > 0 else 0
            remain = max(0, TOTAL_COOK_TIME - elapsed)
            total_str = f"{remain // 60:02d}:{remain % 60:02d}"
            
            if st == "flipped":
                front_sec = int(info["front_duration"])
                back_sec = int(now - info["flip_time"]) if info["flip_time"] > 0 else 0
                phase_label = "뒷면구이"
            else:
                front_sec = elapsed
                back_sec = 0
                phase_label = "앞면구이"
            
            front_str = f"{front_sec // 60:02d}:{front_sec % 60:02d}"
            back_str = f"{back_sec // 60:02d}:{back_sec % 60:02d}"
            
            display_text = (
                f"조리대 {h_id} ({phase_label})\n"
                f"총 잔여: {total_str}\n"
                f"앞 {front_str} | 뒤 {back_str}"
            )
            
            btn.configure(
                text=display_text,
                bg="#2563eb",  # 앞면/뒷면 모두 파란색 점등
                fg="#ffffff",
                font=("Arial", 7, "bold")
            )
        elif st == "finished":
            btn.configure(
                text=f"조리대 {h_id} (HP{hp_no})\n[조리완료 배출대기]\n총 00:00\n서빙 준비중",
                bg="#16a34a",
                fg="#ffffff",
                font=("Arial", 7, "bold")
            )

def get_empty_heat_slot(preferred_plate=None):
    if preferred_plate:
        slots = range(1, 8) if preferred_plate == 1 else range(8, 15)
        for i in slots:
            if heat_units[i]["status"] == "idle":
                return i
    for i in range(1, NUM_SLOTS + 1):
        if heat_units[i]["status"] == "idle":
            return i
    return None

def check_both_plates_flipped():
    """HP1, HP2 둘 다 가동 중인 조리대가 전부 뒷면인지 확인"""
    now = time.time()
    hp1_active = [heat_units[i] for i in range(1, 8) if heat_units[i]["status"] in ["cooking", "flipped"]]
    hp2_active = [heat_units[i] for i in range(8, 15) if heat_units[i]["status"] in ["cooking", "flipped"]]

    if not hp1_active or not hp2_active:
        return False, None

    hp1_all_flipped = all(info["status"] == "flipped" for info in hp1_active)
    hp2_all_flipped = all(info["status"] == "flipped" for info in hp2_active)

    if hp1_all_flipped and hp2_all_flipped:
        hp1_back_duration = max((now - info["flip_time"]) for info in hp1_active)
        hp2_back_duration = max((now - info["flip_time"]) for info in hp2_active)

        longer_plate = 1 if hp1_back_duration >= hp2_back_duration else 2
        print(f"[양쪽 뒷면 감지] HP1 진행: {hp1_back_duration:.1f}s, HP2 진행: {hp2_back_duration:.1f}s -> HP{longer_plate} 앞면 전환 대상")
        return True, longer_plate

    return False, None

def schedule_pipeline():
    global is_unit1_busy, is_unit2_busy

    unit1_slot = board_slot_map.get(1, 1)

    while len(active_orders) < NUM_SLOTS and overflow_orders:
        promoted = overflow_orders.pop(0)
        active_orders.append(promoted)
        print(f"[대기열 승격] T{promoted['table']} {promoted['name']}")

    sync_order_queue_ui()
    sync_connection_info_ui()

    if not is_unit1_busy:
        pending_item = None
        for item in active_orders:
            if item["status"] == "대기":
                pending_item = item
                break

        if not pending_item:
            return

        both_flipped, target_plate = check_both_plates_flipped()

        if both_flipped:
            print(f"\n[인터록 작동] 양쪽 모두 뒷면 -> 뒷면 구이 시간이 더 긴 Heatplate {target_plate}를 앞면으로 전환합니다.")
            target_heat_slot = get_empty_heat_slot(preferred_plate=target_plate)
            if target_heat_slot is None:
                target_heat_slot = get_empty_heat_slot()
                if target_heat_slot is None:
                    print("[알림] 모든 조리대가 가득 찼습니다.")
                    return

            rotate_plate_to_front(target_plate, callback=lambda: _proceed_entry(pending_item, target_heat_slot))
            return

        target_heat_slot = get_empty_heat_slot()
        if target_heat_slot is not None:
            _proceed_entry(pending_item, target_heat_slot)

def rotate_plate_to_front(plate_id, callback=None):
    global is_unit2_busy
    if is_unit2_busy:
        App.after(300, lambda: rotate_plate_to_front(plate_id, callback))
        return

    is_unit2_busy = True
    unit2_slot = board_slot_map.get(2, 2)
    rep_slot = 1 if plate_id == 1 else 8
    
    print(f"▶ [플레이트 반전] Heatplate {plate_id} 회전 모터 구동 -> 앞면 복귀")

    flip_to_front_gcodes = [
        f"G1 X{rep_slot * 200}",
        "M103 P0 S1500 F2000"
    ]

    def _done_rotation():
        global is_unit2_busy
        is_unit2_busy = False
        
        slots = range(1, 8) if plate_id == 1 else range(8, 15)
        for s in slots:
            if heat_units[s]["status"] == "flipped":
                heat_units[s]["status"] = "cooking"
                heat_units[s]["flipped"] = False
                if heat_units[s]["order"]:
                    heat_units[s]["order"]["status"] = "4단계:조리(앞)"

        print(f"▶ [반전 완료] Heatplate {plate_id} 앞면 복귀 완료 (파란색 점등 및 새 메뉴 수용)")
        sync_order_queue_ui()
        sync_heat_units_ui()
        
        if callback:
            callback()

    execute_gcode_sequence(unit2_slot, flip_to_front_gcodes, on_done=_done_rotation)

def _proceed_entry(pending_item, target_heat_slot):
    global is_unit1_busy
    unit1_slot = board_slot_map.get(1, 1)

    is_unit1_busy = True
    pending_item["status"] = "1단계:Pick"
    pending_item["assigned_slot"] = target_heat_slot
    
    heat_units[target_heat_slot]["status"] = "reserved"
    sync_order_queue_ui()
    sync_heat_units_ui()
    
    plate_no = heat_units[target_heat_slot]["plate_id"]
    print(f"\n▶ [1단계 시작: Pick and place] T{pending_item['table']} {pending_item['name']} -> 조리대 {target_heat_slot} (HP{plate_no})")
    
    gcode_list = get_stage1_pick_gcode(pending_item["name"])
    execute_gcode_sequence(
        slot_id=unit1_slot,
        gcodes=gcode_list,
        on_done=lambda target=pending_item: start_stage2_unit_change(target)
    )

def start_stage2_unit_change(item):
    global is_unit2_busy
    unit1_slot = board_slot_map.get(1, 1)
    unit2_slot = board_slot_map.get(2, 2)

    item["status"] = "2단계:Change"
    sync_order_queue_ui()
    print(f"\n▶ [2단계 시작: Unit change] T{item['table']} {item['name']}")

    def _wait_and_transfer():
        global is_unit2_busy
        if is_unit2_busy:
            App.after(100, _wait_and_transfer)
            return

        is_unit2_busy = True
        execute_gcode_sequence(unit1_slot, GCODE_UNIT1_CHANGE, on_done=_step2_grip)

    def _step2_grip():
        execute_gcode_sequence(unit2_slot, GCODE_UNIT2_GRIP, on_done=_step2_release)

    def _step2_release():
        global is_unit1_busy
        def _on_unit1_free():
            global is_unit1_busy
            is_unit1_busy = False
            schedule_pipeline()

        execute_gcode_sequence(unit1_slot, GCODE_UNIT1_RELEASE, on_done=_on_unit1_free)
        start_stage3_cook_and_place(item)

    _wait_and_transfer()

def start_stage3_cook_and_place(item):
    unit2_slot = board_slot_map.get(2, 2)
    heat_slot = item["assigned_slot"]
    plate_no = heat_units[heat_slot]["plate_id"]
    
    item["status"] = "3단계:CookPlace"
    sync_order_queue_ui()
    print(f"\n▶ [3단계 시작: Cook and place] 조리대 {heat_slot} (HP{plate_no}) 안착 이동")

    target_x = heat_slot * 200

    gcode_cook_place = [
        f"G1 X{target_x}",
        "G1 Z1500 Y1500",
        "M800 P0 S0",
        "G28 Z Y"
    ]

    def _on_placed():
        global is_unit2_busy
        is_unit2_busy = False
        
        # 4단계 시작: 앞면 조리 및 파란색 점등
        item["status"] = "4단계:조리(앞)"
        heat_units[heat_slot]["status"] = "cooking"
        heat_units[heat_slot]["start_time"] = time.time()
        heat_units[heat_slot]["front_duration"] = 0
        heat_units[heat_slot]["flip_time"] = 0
        heat_units[heat_slot]["order"] = item
        heat_units[heat_slot]["flipped"] = False
        
        sync_order_queue_ui()
        sync_heat_units_ui()
        print(f"[3단계 완료] 조리대 {heat_slot} 안착 완료 (파란색 점등 및 조리 타이머 가동)")
        schedule_pipeline()

    execute_gcode_sequence(unit2_slot, gcode_cook_place, on_done=_on_placed)

# ----------------------------------------------------
# 7. 4단계 조리 스레드 (플레이트 단위 동기화 뒤집기 & 12분 완제)
# ----------------------------------------------------
def background_cooking_timer_monitor():
    """
    1-7번(HP1), 8-14번(HP2)는 일체형으로 동시에 움직임.
    플레이트 내 하나라도 3분(180초) 초과 시 해당 플레이트 전체가 뒷면으로 전환됨.
    """
    while is_running:
        now = time.time()
        plate_groups = {
            1: range(1, 8),
            2: range(8, 15)
        }

        # 1) 플레이트 단위 3분 경과 체크 및 일괄 뒤집기
        for plate_id, slot_range in plate_groups.items():
            should_flip_plate = False
            for s in slot_range:
                info = heat_units[s]
                if info["status"] == "cooking" and not info["flipped"]:
                    elapsed = now - info["start_time"]
                    if elapsed >= FLIP_TIME:
                        should_flip_plate = True
                        break

            # 해당 플레이트에 3분 넘긴 음식이 1개라도 있으면 해당 플레이트 전체 일괄 뒷면 전환
            if should_flip_plate:
                print(f"\n[플레이트 연동 감지] Heatplate {plate_id} 내 3분 초과 조리대 발생 -> 플레이트 전체 뒷면 일괄 전환")
                for s in slot_range:
                    info = heat_units[s]
                    if info["status"] == "cooking" and not info["flipped"]:
                        info["flipped"] = True
                        info["status"] = "flipped"
                        info["front_duration"] = now - info["start_time"]  # 앞면 조리 시간 확정
                        info["flip_time"] = now                            # 뒷면 시작 시간 기록
                        if info["order"]:
                            info["order"]["status"] = "4단계:뒤집힘(뒷)"
                
                # 플레이트 전체 회전 G-code 실행
                trigger_plate_flip(plate_id)

        # 2) 12분 만료 슬롯 개별 배출 검사
        for h_id, info in heat_units.items():
            if info["status"] in ["cooking", "flipped"]:
                elapsed = now - info["start_time"]
                if elapsed >= TOTAL_COOK_TIME:
                    info["status"] = "finished"
                    if info["order"]:
                        info["order"]["status"] = "5단계:완성배출"
                    print(f"[조리 완료] 조리대 {h_id} (HP{info['plate_id']}) 12분 만료 배출")
                    trigger_stage5_finish(h_id)

        time.sleep(0.5)

def trigger_plate_flip(plate_id):
    """지정된 플레이트 전체를 뒤집는 시퀀스 전송"""
    global is_unit2_busy
    if is_unit2_busy:
        App.after(300, lambda: trigger_plate_flip(plate_id))
        return

    is_unit2_busy = True
    unit2_slot = board_slot_map.get(2, 2)
    rep_slot = 1 if plate_id == 1 else 8
    print(f"▶ [플레이트 일괄 뒤집기] Heatplate {plate_id} 회전 구동")

    flip_gcodes = [
        f"G1 X{rep_slot * 200}",
        "M103 P0 S1500 F2000"
    ]

    def _done_flip():
        global is_unit2_busy
        is_unit2_busy = False
        print(f"▶ [뒤집기 완료] Heatplate {plate_id} 전체 뒷면 전환 완료 (파란색 유지)")
        sync_order_queue_ui()
        sync_heat_units_ui()
        schedule_pipeline()

    execute_gcode_sequence(unit2_slot, flip_gcodes, on_done=_done_flip)

def trigger_stage5_finish(slot_idx):
    global is_unit2_busy
    if is_unit2_busy:
        App.after(500, lambda: trigger_stage5_finish(slot_idx))
        return

    is_unit2_busy = True
    unit2_slot = board_slot_map.get(2, 2)
    plate_no = heat_units[slot_idx]["plate_id"]
    print(f"\n▶ [5단계: Goto finish] 조리대 {slot_idx} (HP{plate_no}) 완료 배출 시작")

    finish_gcodes = [
        f"G1 X{slot_idx * 200}"
    ] + GCODE_UNIT2_FINISH

    def _done_finish():
        global is_unit2_busy
        is_unit2_busy = False
        
        target_order = heat_units[slot_idx]["order"]
        if target_order and target_order in active_orders:
            active_orders.remove(target_order)
            print(f"[최종 서빙 완료] T{target_order['table']} {target_order['name']}")

        heat_units[slot_idx]["status"] = "idle"
        heat_units[slot_idx]["order"] = None
        heat_units[slot_idx]["start_time"] = 0
        heat_units[slot_idx]["flip_time"] = 0
        heat_units[slot_idx]["front_duration"] = 0
        heat_units[slot_idx]["flipped"] = False

        sync_order_queue_ui()
        sync_heat_units_ui()
        schedule_pipeline()

    execute_gcode_sequence(unit2_slot, finish_gcodes, on_done=_done_finish)

# ----------------------------------------------------
# 8. UI 이벤트 및 테이블 관리
# ----------------------------------------------------
def sync_connection_info_ui():
    table_overflow_stats = {}
    for item in overflow_orders:
        t_id = item["table"]
        if t_id not in table_overflow_stats:
            table_overflow_stats[t_id] = {
                "total": item["total_order"],
                "remaining": 0
            }
        table_overflow_stats[t_id]["remaining"] += 1

    slot_keys = list(table_overflow_stats.keys())

    for i in range(1, NUM_SLOTS + 1):
        idx = i - 1
        if idx < len(slot_keys):
            t_id = slot_keys[idx]
            tot = table_overflow_stats[t_id]["total"]
            rem = table_overflow_stats[t_id]["remaining"]
            
            c0_text = f"{t_id}테이블"
            c1_text = f"{tot}개메뉴"
            c2_text = f"{rem}개 남음"
            fg_color = "#d97706"
        else:
            c0_text = "-"
            c1_text = "-"
            c2_text = "-"
            fg_color = "black"

        if i < len(c0Label) and c0Label[i].winfo_exists():
            c0Label[i].configure(text=c0_text)
        if i < len(c1Label) and c1Label[i].winfo_exists():
            c1Label[i].configure(text=c1_text)
        if i < len(c2Label) and c2Label[i].winfo_exists():
            c2Label[i].configure(text=c2_text, fg=fg_color)

def sync_menu_counter_ui():
    for idx in range(4):
        if idx < len(menu_buttons) and menu_buttons[idx].winfo_exists():
            menu_buttons[idx].configure(text=f"{MENU_NAMES[idx]} ({menu_counter[idx]})")

def add_menu_count(idx):
    menu_counter[idx] += 1
    sync_menu_counter_ui()

def reset_menu_count():
    global menu_counter
    menu_counter = [0, 0, 0, 0]
    sync_menu_counter_ui()

def update_table_ui(t_idx):
    if t_idx < len(table_buttons) and table_buttons[t_idx].winfo_exists():
        count = table_orders[t_idx]["count"]
        amt = table_orders[t_idx]["amount"]
        table_buttons[t_idx].configure(text=f"{t_idx + 1}테이블주문 ({count})\n{amt:,}원")

    if t_idx < len(table_order_detail_labels) and table_order_detail_labels[t_idx].winfo_exists():
        items_dict = table_orders[t_idx].get("items", {})
        active_items = [f"{name} x {qty}" for name, qty in items_dict.items() if qty > 0]
        if active_items:
            detail_text = "\n".join(active_items)
            fg_color = "#1e293b"
        else:
            detail_text = "-"
            fg_color = "#94a3b8"
        table_order_detail_labels[t_idx].configure(text=detail_text, fg=fg_color)

def handle_table_button(t_idx):
    global menu_counter, table_orders
    current_selected_sum = sum(menu_counter)

    if current_selected_sum > 0:
        added_amount = current_selected_sum * MENU_PRICE
        table_orders[t_idx]["count"] += current_selected_sum
        table_orders[t_idx]["amount"] += added_amount

        for m_idx, count in enumerate(menu_counter):
            if count > 0:
                table_orders[t_idx]["items"][MENU_NAMES[m_idx]] += count

        update_table_ui(t_idx)

        t_num = t_idx + 1
        total_order_cnt = current_selected_sum
        print(f"[{t_num}테이블 접수] {total_order_cnt}건")

        ordered_items = []
        for m_idx, count in enumerate(menu_counter):
            for _ in range(count):
                ordered_items.append({
                    "table": t_num,
                    "name": MENU_NAMES[m_idx],
                    "status": "대기",
                    "total_order": total_order_cnt,
                    "assigned_slot": None
                })

        for item in ordered_items:
            if len(active_orders) < NUM_SLOTS:
                active_orders.append(item)
            else:
                overflow_orders.append(item)

        menu_counter = [0, 0, 0, 0]
        sync_menu_counter_ui()
        sync_order_queue_ui()
        sync_connection_info_ui()

        schedule_pipeline()
    else:
        if table_orders[t_idx]["count"] > 0 or table_orders[t_idx]["amount"] > 0:
            print(f"[{t_idx + 1}테이블 정산 완료]")
            table_orders[t_idx]["count"] = 0
            table_orders[t_idx]["amount"] = 0
            table_orders[t_idx]["items"] = {name: 0 for name in MENU_NAMES}
            update_table_ui(t_idx)

# ----------------------------------------------------
# 9. 시스템 모니터링
# ----------------------------------------------------
def background_system_monitor():
    psutil.cpu_percent(interval=None)
    while is_running:
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            vm = psutil.virtual_memory()
            ram_pct = vm.percent
            ram_used = vm.used / (1024 ** 3)
            ram_tot = vm.total / (1024 ** 3)

            gpu_load_str = "N/A"
            vram_str = "N/A"

            if HAS_NVML:
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_load_str = f"{util.gpu}%"

                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    vram_used_gb = mem_info.used / (1024 ** 3)
                    vram_tot_gb = mem_info.total / (1024 ** 3)
                    vram_pct = (mem_info.used / mem_info.total) * 100
                    vram_str = f"{vram_pct:.1f}% ({vram_used_gb:.1f}/{vram_tot_gb:.1f} GB)"
                except Exception:
                    pass

            current_sys_metrics["cpu"] = cpu
            current_sys_metrics["ram_pct"] = ram_pct
            current_sys_metrics["ram_used_gb"] = ram_used
            current_sys_metrics["ram_total_gb"] = ram_tot
            current_sys_metrics["gpu_load"] = gpu_load_str
            current_sys_metrics["vram_used"] = vram_str

        except Exception:
            pass

        time.sleep(0.5)

def update_system_statusbar():
    if not is_running or not App.winfo_exists():
        return

    cpu = current_sys_metrics["cpu"]
    ram_pct = current_sys_metrics["ram_pct"]
    ram_used = current_sys_metrics["ram_used_gb"]
    ram_tot = current_sys_metrics["ram_total_gb"]
    gpu_load = current_sys_metrics["gpu_load"]
    vram_used = current_sys_metrics["vram_used"]

    status_str = (
        f" [CPU] {cpu:4.1f}%   |   "
        f"[RAM] {ram_pct:4.1f}% ({ram_used:.1f}/{ram_tot:.1f} GB)   |   "
        f"[GPU] {gpu_load}   |   "
        f"[GPU VRAM] {vram_used}   |   "
        f"[MODE] {'SIMULATION (NO OK REQ)' if SIMULATION_MODE else 'HARDWARE SERIAL'}"
    )

    if sys_status_label.winfo_exists():
        sys_status_label.config(text=status_str)
    
    sync_heat_units_ui()

    if is_running and App.winfo_exists():
        App.after(1000, update_system_statusbar)

# ----------------------------------------------------
# 10. GUI 레이아웃 구성
# ----------------------------------------------------
App = tk.Tk()
App.title('Food Automation Orchestrator - Plate Synchronized Flip')
App.resizable(width=True, height=True)
App.geometry('1920x860+40+30')

App.columnconfigure(0, weight=1)
App.rowconfigure(0, weight=1)
App.rowconfigure(1, weight=0)

content_frame = tk.Frame(App)
content_frame.grid(row=0, column=0, sticky="nsew")

content_frame.columnconfigure(0, weight=5)
content_frame.columnconfigure(1, weight=0)
content_frame.columnconfigure(2, weight=3)
content_frame.columnconfigure(3, weight=3)
content_frame.columnconfigure(4, weight=3)
content_frame.rowconfigure(0, weight=1)

left_main_panel = tk.Frame(content_frame)
left_main_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

# 가운데 14개 가상 조리대 버튼 패널
slot_btn_panel = tk.LabelFrame(content_frame, text="가상 조리대 (1~14)", padx=4, pady=4)
slot_btn_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 5), pady=5)

slot_dummy_buttons.clear()
for i in range(14):
    slot_btn_panel.rowconfigure(i, weight=1)
    hp_no = 1 if i < 7 else 2
    btn = tk.Button(
        slot_btn_panel,
        text=f"조리대 {i+1} (HP{hp_no})\n[비어있음]\n총 00:00\n앞 00:00 | 뒤 00:00",
        font=("Arial", 7),
        bg="#e2e8f0",
        fg="#64748b",
        relief="groove",
        width=18
    )
    btn.grid(row=i, column=0, sticky="nsew", padx=1, pady=1)
    slot_dummy_buttons.append(btn)

right_camera_panel = tk.Frame(content_frame, width=320)
right_camera_panel.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

analysis_panel = tk.Frame(content_frame, width=320)
analysis_panel.grid(row=0, column=3, sticky="nsew", padx=5, pady=5)

chat_panel = tk.Frame(content_frame, width=350)
chat_panel.grid(row=0, column=4, sticky="nsew", padx=5, pady=5)

left_main_panel.columnconfigure(0, weight=1)
left_main_panel.columnconfigure(1, weight=1)
left_main_panel.columnconfigure(2, weight=1)
left_main_panel.rowconfigure(5, weight=1)

topmenu = tk.Menu(App)
filemenu = tk.Menu(topmenu, tearoff=0)
filemenu.add_command(label='Auto Connect', command=autoDetectAndConnect)
filemenu.add_command(label='Disconnect All', command=serialDisconnectAll)
filemenu.add_separator()
filemenu.add_command(label='Emergency Stop (Unit 1)', command=lambda: send_slot_command(board_slot_map.get(1, 1), "M112"))
filemenu.add_command(label='Emergency Stop (Unit 2)', command=lambda: send_slot_command(board_slot_map.get(2, 2), "M112"))
filemenu.add_separator()
filemenu.add_command(label='Send Entries', command=c7entrySender)
topmenu.add_cascade(label='Port Manager', menu=filemenu)
App.config(menu=topmenu)

# LF1
myLF1 = tk.LabelFrame(left_main_panel, text='Connection Info', padx=2, pady=1, labelanchor='n')
myLF1.grid(row=0, column=0, padx=5, pady=3, sticky="nsew")

for count, name in enumerate(portName):
    lbl = tk.Label(myLF1, text=name, padx=3, pady=1, font=("Arial", 9))
    lbl.grid(row=count, column=0, sticky='w')
    c0Label.append(lbl)

for count, stat in enumerate(initStat):
    lbl = tk.Label(myLF1, text=stat, padx=3, pady=1, font=("Arial", 9))
    lbl.grid(row=count, column=1)
    c1Label.append(lbl)

for count, buff in enumerate(initBuffer):
    lbl = tk.Label(myLF1, text=buff, padx=3, pady=1, font=("Arial", 9))
    lbl.grid(row=count, column=2)
    c2Label.append(lbl)

# LF2
myLF2 = tk.LabelFrame(left_main_panel, text='5-Stage Order Pipeline', padx=2, pady=1, labelanchor='n')
myLF2.grid(row=0, column=1, padx=5, pady=3, sticky="nsew")

for count, name in enumerate(LF2body):
    lbl = tk.Label(myLF2, text=name, padx=3, pady=1, font=("Arial", 9))
    lbl.grid(row=count, column=0)
    c3Label.append(lbl)

for count, val in enumerate(LF2body_value):
    lbl = tk.Label(myLF2, text=val, padx=3, pady=1, font=("Arial", 9))
    lbl.grid(row=count, column=1)
    c4Label.append(lbl)

# LF3
myLF3 = tk.LabelFrame(left_main_panel, text='Serial Slots (U1: Slot 1 / U2: Slot 2)', padx=2, pady=1, labelanchor='n')
myLF3.grid(row=0, column=2, padx=5, pady=3, sticky="nsew")

for count, dev in enumerate(LF3cmos):
    lbl = tk.Label(myLF3, text=dev, padx=2, pady=1, font=("Arial", 9))
    lbl.grid(row=count, column=0)
    c5Label.append(lbl)

for count, stat in enumerate(LF3cmos_value):
    lbl = tk.Label(myLF3, text=stat, padx=2, pady=1, font=("Arial", 9))
    lbl.grid(row=count, column=1)
    c6Label.append(lbl)

for count, entry_name in enumerate(LF3cmos_entry):
    if count == 0:
        btn = tk.Button(myLF3, text='전송', width=5, pady=0, font=("Arial", 8), command=c7entrySender)
        btn.grid(row=count, column=2, padx=1, pady=0)
        c7Entry.append(btn)
    else:
        ent = tk.Entry(myLF3, width=7, font=("Arial", 9))
        ent.grid(row=count, column=2, padx=1, pady=0)
        ent.bind('<Return>', lambda event, idx=count: (
            send_slot_command(idx, event.widget.get().strip()),
            event.widget.delete(0, tk.END)
        ))
        c7Entry.append(ent)

# 1층: 메뉴 수량 선택
mid_frame = tk.Frame(left_main_panel, pady=2)
mid_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=2)

button_specs = [
    {"name": "닭고기", "color": "#d9ead3", "is_reset_btn": False},
    {"name": "목살",   "color": "#fff2cc", "is_reset_btn": False},
    {"name": "삼겹살", "color": "#e2e2e2", "is_reset_btn": False},
    {"name": "양념",   "color": "#e0f2fe", "is_reset_btn": False},
    {"name": "초기화", "color": "#f4cccc", "is_reset_btn": True}
]

menu_buttons.clear()
for i, spec in enumerate(button_specs):
    mid_frame.columnconfigure(i, weight=1)
    if not spec["is_reset_btn"]:
        btn = tk.Button(
            mid_frame,
            text=f"{spec['name']} (0)",
            bg=spec["color"],
            height=2,
            command=lambda idx=i: add_menu_count(idx)
        )
        menu_buttons.append(btn)
    else:
        btn = tk.Button(
            mid_frame,
            text=spec["name"],
            bg=spec["color"],
            height=2,
            command=reset_menu_count
        )
    btn.grid(row=0, column=i, padx=2, sticky="ew")

# 2층: 테이블 주문 버튼
sub_btn_frame = tk.Frame(left_main_panel, pady=2)
sub_btn_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=5, pady=2)

table_buttons.clear()
for i in range(5):
    sub_btn_frame.columnconfigure(i, weight=1)
    btn = tk.Button(
        sub_btn_frame,
        text=f"{i+1}테이블주문 (0)\n0원",
        bg="#f0f0f0",
        height=2,
        command=lambda idx=i: handle_table_button(idx)
    )
    btn.grid(row=0, column=i, padx=2, sticky="ew")
    table_buttons.append(btn)

# 3층: 보조 버튼
extra_btn_frame = tk.Frame(left_main_panel, pady=2)
extra_btn_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=5, pady=2)

dummy_buttons.clear()
for i in range(5):
    extra_btn_frame.columnconfigure(i, weight=1)
    btn = tk.Button(
        extra_btn_frame,
        text=f"빈버튼 {i+1}",
        bg="#f8f9fa",
        height=2
    )
    btn.grid(row=0, column=i, padx=2, sticky="ew")
    dummy_buttons.append(btn)

# 4층: 테이블별 주문 상세 내역
table_order_detail_frame = tk.LabelFrame(left_main_panel, text='정산 전 테이블별 주문 상세 내역', padx=5, pady=3)
table_order_detail_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5, pady=3)

table_order_detail_labels.clear()
for i in range(5):
    table_order_detail_frame.columnconfigure(i, weight=1)
    t_box = tk.Frame(table_order_detail_frame, bg="#ffffff", relief="solid", bd=1, padx=3, pady=3)
    t_box.grid(row=0, column=i, padx=2, sticky="nsew")
    
    t_title = tk.Label(t_box, text=f"{i+1}번 테이블", font=("Arial", 9, "bold"), bg="#e2e8f0", fg="#1e293b")
    t_title.pack(fill="x", pady=(0, 2))
    
    d_lbl = tk.Label(
        t_box,
        text="-",
        font=("Arial", 8),
        bg="#ffffff",
        fg="#94a3b8",
        justify="center",
        height=4
    )
    d_lbl.pack(fill="both", expand=True)
    table_order_detail_labels.append(d_lbl)

# 5층: 콘솔 창
console_frame = tk.LabelFrame(left_main_panel, text='Console Monitoring', padx=5, pady=3)
console_frame.grid(row=5, column=0, columnspan=3, padx=5, pady=3, sticky="nsew")

font_family = "Courier" if sys.platform == "darwin" else "Consolas"
console_text = tk.Text(
    console_frame,
    height=7,
    bg="#1e1e1e",
    fg="#d4d4d4",
    font=(font_family, 9),
    wrap="char",
    state="disabled"
)
console_text.pack(side='left', fill='both', expand=True)

scrollbar = ttk.Scrollbar(console_frame, orient="vertical", command=console_text.yview)
scrollbar.pack(side='right', fill='y')
console_text.configure(yscrollcommand=scrollbar.set)

console_text.tag_config('out', foreground='#d4d4d4')
console_text.tag_config('error', foreground='#f48771')

sys.stdout = ConsoleRedirector(console_text, orig_stdout, tag='out')
sys.stderr = ConsoleRedirector(console_text, orig_stderr, tag='error')

# 8. 우측 카메라 패널
right_camera_panel.rowconfigure(0, weight=1)
right_camera_panel.rowconfigure(1, weight=1)
right_camera_panel.rowconfigure(2, weight=1)
right_camera_panel.columnconfigure(0, weight=1)

cam_titles = ["Camera 1 (Unit 1 이송부)", "Camera 2 (Unit Change 구역)", "Camera 3 (Heatplates 조리부)"]
for idx, title in enumerate(cam_titles):
    cam_lf = tk.LabelFrame(right_camera_panel, text=title, padx=5, pady=5)
    cam_lf.grid(row=idx, column=0, sticky="nsew", padx=3, pady=3)
    disp_lbl = tk.Label(cam_lf, text=f"CAM {idx+1}\n(Standby)", bg="#111111", fg="#777777", font=("Arial", 12))
    disp_lbl.pack(fill="both", expand=True)
    cam_display_labels.append(disp_lbl)

# 8-1. 우측 비전 분석 패널
analysis_panel.rowconfigure(0, weight=1)
analysis_panel.rowconfigure(1, weight=1)
analysis_panel.rowconfigure(2, weight=1)
analysis_panel.columnconfigure(0, weight=1)

analysis_titles = [
    "Vision #1 상태 분석",
    "Vision #2 상태 분석",
    "Vision #3 상태 분석"
]

for section_idx, title in enumerate(analysis_titles):
    sec_lf = tk.LabelFrame(analysis_panel, text=title, padx=4, pady=4)
    sec_lf.grid(row=section_idx, column=0, sticky="nsew", padx=3, pady=3)

    for r in range(3):
        sec_lf.rowconfigure(r, weight=1)
    for c in range(3):
        sec_lf.columnconfigure(c, weight=1)

    for b_idx in range(9):
        r = b_idx // 3
        c = b_idx % 3
        btn = tk.Button(
            sec_lf,
            text=f"S{section_idx+1}-P{b_idx+1}\n[OK]",
            font=("Arial", 8),
            bg="#f1f5f9",
            padx=2,
            pady=2
        )
        btn.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
        analysis_buttons[section_idx].append(btn)

# 8-2. Ollama AI 어시스턴트 채팅창
chat_panel.rowconfigure(0, weight=1)
chat_panel.columnconfigure(0, weight=1)

chat_lf = tk.LabelFrame(chat_panel, text='Ollama AI Assistant (Chat)', padx=5, pady=5)
chat_lf.grid(row=0, column=0, sticky="nsew")
chat_lf.rowconfigure(0, weight=1)
chat_lf.rowconfigure(1, weight=0)
chat_lf.columnconfigure(0, weight=1)

chat_history = tk.Text(chat_lf, bg="#0f172a", fg="#f8fafc", font=("Arial", 9), wrap="word", state="disabled")
chat_history.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

chat_history.tag_config('user', foreground='#38bdf8', font=("Arial", 9, "bold"))
chat_history.tag_config('bot', foreground='#4ade80')
chat_history.tag_config('sys', foreground='#94a3b8', font=("Arial", 8, "italic"))

chat_scroll = ttk.Scrollbar(chat_lf, orient="vertical", command=chat_history.yview)
chat_scroll.grid(row=0, column=1, sticky="ns", pady=(0, 5))
chat_history.configure(yscrollcommand=chat_scroll.set)

chat_history.configure(state='normal')
chat_history.insert(tk.END, "[시스템] 플레이트 단위(1~7, 8~14) 일체형 뒤집기 모니터 가동 완료.\n", "sys")
chat_history.configure(state='disabled')

chat_input_frame = tk.Frame(chat_lf)
chat_input_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
chat_input_frame.columnconfigure(0, weight=1)

chat_entry = tk.Entry(chat_input_frame, font=("Arial", 10))
chat_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4), ipady=3)

def append_chat_message(sender_tag, message):
    if not is_running or not App.winfo_exists():
        return
    chat_history.configure(state='normal')
    if sender_tag == 'user':
        chat_history.insert(tk.END, f"\n[User]: {message}\n", "user")
    elif sender_tag == 'bot':
        chat_history.insert(tk.END, f"[Ollama]: {message}\n", "bot")
    elif sender_tag == 'sys':
        chat_history.insert(tk.END, f"[System]: {message}\n", "sys")
    chat_history.see(tk.END)
    chat_history.configure(state='disabled')

def send_chat_message():
    user_text = chat_entry.get().strip()
    if not user_text:
        return
    chat_entry.delete(0, tk.END)
    append_chat_message('user', user_text)

    def _async_ollama_mock():
        time.sleep(0.3)
        mock_reply = f"명령 '{user_text}'을(를) 수신했습니다. 플레이트 동기화 상태를 모니터링 중입니다."
        if is_running and App.winfo_exists():
            App.after(0, lambda: append_chat_message('bot', mock_reply))

    threading.Thread(target=_async_ollama_mock, daemon=True).start()

chat_entry.bind('<Return>', lambda e: send_chat_message())

chat_btn_box = tk.Frame(chat_input_frame)
chat_btn_box.grid(row=0, column=1)

chat_send_btn = tk.Button(chat_btn_box, text="전송", bg="#3b82f6", fg="white", font=("Arial", 9, "bold"), command=send_chat_message)
chat_send_btn.pack(side="left", padx=1)

# 최하단 상태바
status_bar_frame = tk.Frame(App, bg="#202020", relief="sunken", bd=1)
status_bar_frame.grid(row=1, column=0, sticky="ew")

sys_status_label = tk.Label(
    status_bar_frame,
    text=" [CPU] 0.0%   |   [RAM] 0.0% (0.0/0.0 GB)   |   [GPU] N/A   |   [GPU VRAM] N/A",
    font=("Consolas" if sys.platform != "darwin" else "Courier", 9),
    bg="#202020",
    fg="#00e676",
    anchor="w",
    padx=8,
    pady=3
)
sys_status_label.pack(side="left", fill="x", expand=True)

def on_closing():
    global is_running
    is_running = False
    serialDisconnectAll()
    if HAS_NVML:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass
    sys.stdout = orig_stdout
    sys.stderr = orig_stderr
    App.destroy()

if __name__ == '__main__':
    monitor_thread = threading.Thread(target=background_system_monitor, daemon=True)
    monitor_thread.start()

    # 플레이트 단위 동기화 조리 타이머 스레드
    cooking_timer_thread = threading.Thread(target=background_cooking_timer_monitor, daemon=True)
    cooking_timer_thread.start()

    sync_menu_counter_ui()
    sync_order_queue_ui()
    sync_connection_info_ui()
    
    for i in range(5):
        update_table_ui(i)
    
    App.protocol("WM_DELETE_WINDOW", on_closing)
    App.after(100, serialTester)
    App.after(300, update_system_statusbar)
    App.mainloop()