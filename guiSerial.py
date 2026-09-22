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
# [설정] 실전 공정 타이머 임계치 설정 (초 단위)
# ----------------------------------------------------
SIMULATION_MODE = False     # False: 실제 센서/모터 하드웨어 연동 구동
SIM_STEP_DELAY_MS = 60

MENU_NAMES = ["닭고기", "목살", "삼겹살", "양념"]
MENU_PRICE = 6000

# [운영 기준 시간 설정]
TIMER_TOTAL_MAX = 720.0          # 1번: 총 조리시간 상한 12분 (720초)
TIMER_PHASE_MAX = 360.0          # 2, 3번: 앞면 / 뒷면 조리시간 각 상한 6분 (360초)
TIMER_UNIT_STAY_MAX = 120.0      # 4번: Heat unit 위상 연속 체류 상한 2분 (120초)
TIMER_BLOCK_AND_FINISH = 690.0   # 배출 트리거 및 2, 3단계 차단 임계치 11분 30초 (690초)
TIMER_STAGE3_MIN_REMAIN = 20.0   # 3단계 진입 조건: 위상 반전까지 남은 시간 최소 20초 이상

NUM_SLOTS = 14

# ----------------------------------------------------
# 1. 5단계 시퀀스 G-code 생성 함수
# ----------------------------------------------------
def get_stage1_pick_gcode(menu_name):
    x_positions = {
        "닭고기": 2000,
        "목살": 2500,
        "삼겹살": 3000,
        "양념": 3500
    }
    x_val = x_positions.get(menu_name, 2000)
    return [
        "G28",
        "M119",
        "M103 P0 S2000 F2000 D0",
        "M103 P1 S2000 F2000 D0",
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
        "G28 Z Y",
        "M103 P0 S2000 F1500 D1",
        "M103 P1 S2000 F1500 D1",
        "M119"
    ]

def get_stage2_unit2_approach_gcode(b1_x):
    target_x = b1_x + 2500
    return [
        "M119",
        f"G1 X{target_x}",
        "G38"
    ]

GCODE_STAGE2_UNIT1_DOCK = ["G40"]
GCODE_STAGE2_UNIT2_GRIP = ["M800 P0 S1", "G4 P2000"]
GCODE_STAGE2_UNIT1_RELEASE = ["M800 P0 S0", "M800 P1 S0", "G4 P2000", "G28"]

def get_stage3_cook_place_gcode(slot_id):
    target_x = slot_id * 200
    return [
        f"G1 X{target_x}",
        "G1 Z1500 Y1500",
        "M800 P0 S0",
        "G4 P1000",
        "M800 P2 S1",
        "G28 Z Y"
    ]

def get_stage4_flip_gcode(plate_id, to_side):
    """
    to_side: 'back'(앞->뒤, D0.) or 'front'(뒤->앞, D1.)
    plate_id: 1(P0) or 2(P1)
    """
    p_num = 0 if plate_id == 1 else 1
    d_param = "D0." if to_side == "back" else "D1."
    return [
        f"M103 P{p_num} S2000 F2000 {d_param}",
        "M119"
    ]

def get_stage5_finish_gcode(slot_id):
    target_x = slot_id * 200
    return [
        f"G1 X{target_x}",
        "G28 Y",
        "G28 Z",
        "M800 P0 S1",
        "G1 Y1500 Z1500",
        "G28 X",
        "M800 P0 S0"
    ]

# ----------------------------------------------------
# 2. 전역 상태 및 5종 타이머 관리 구조
# ----------------------------------------------------
# 규칙 1: Heat Unit 1과 2는 상호 반대 위상 배치
plate_current_side = {1: "front", 2: "back"}
plate_flipping_lock = {1: False, 2: False}

heat_units = {
    i: {
        "status": "idle",             # 'idle', 'reserved', 'cooking', 'finished'
        "plate_id": 1 if i <= 7 else 2,
        "order": None,
        "total_cook_time": 0.0,       # 1. 총 조리시간 (최대 12분)
        "front_cook_time": 0.0,       # 2. 앞면 총 조리시간 (최대 6분)
        "back_cook_time": 0.0,        # 3. 뒷면 총 조리시간 (최대 6분)
        "heat_unit_stay_time": 0.0,   # 4. 현 위상 연속 체류시간 (최대 2분)
        "total_process_time": 0.0,    # 5. 전체 공정 누적시간
        "last_tick": 0.0
    }
    for i in range(1, NUM_SLOTS + 1)
}

# 플레이트 자체 위상 전환 타이머 (각각 2분 주기 추적)
plate_phase_timer = {1: 0.0, 2: 0.0}
plate_last_tick = time.time()

sensor_states = {
    "stm1_pc7": "no trigger",
    "stm1_pd2": "no trigger",
    "stm2_pd2": "no trigger"
}

menu_counter = [0, 0, 0, 0]
menu_buttons = []
table_orders = [{"count": 0, "amount": 0, "items": {name: 0 for name in MENU_NAMES}} for _ in range(5)]
table_buttons = []
table_order_detail_labels = []
cancel_table_buttons = []

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
unit2_at_prepick_pos = True

current_sys_metrics = {
    "cpu": 0.0, "ram_pct": 0.0, "ram_used_gb": 0.0,
    "ram_total_gb": 0.0, "gpu_load": "N/A", "vram_used": "N/A"
}

# ----------------------------------------------------
# 3. 콘솔 리다이렉터
# ----------------------------------------------------
class ConsoleRedirector:
    def __init__(self, text_widget, original_stream, tag='out', max_lines=80):
        self.text_widget = text_widget
        self.original_stream = original_stream
        self.tag = tag
        self.max_lines = max_lines
        self.buffer = deque()
        self.scheduled = False

    def write(self, string):
        if self.original_stream:
            self.original_stream.write(string)
            self.original_stream.flush()

        if not string or not is_running:
            return

        self.buffer.append(string)
        if not self.scheduled:
            self.scheduled = True
            try:
                if is_running and self.text_widget.winfo_exists():
                    self.text_widget.after(30, self._flush_to_widget)
            except Exception:
                pass

    def _flush_to_widget(self):
        self.scheduled = False
        if not is_running or not self.text_widget.winfo_exists():
            return
        
        chunk = ""
        while self.buffer:
            chunk += self.buffer.popleft()

        try:
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, chunk, self.tag)
            num_lines = int(self.text_widget.index('end-1c').split('.')[0])
            if num_lines > self.max_lines:
                self.text_widget.delete('1.0', f'{num_lines - self.max_lines}.0')
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        except Exception:
            pass

    def flush(self):
        if self.original_stream:
            self.original_stream.flush()

# ----------------------------------------------------
# 4. G-code 비동기 엔진
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
                if not SIMULATION_MODE:
                    send_slot_command(slot_id, cmd)
                actual_delay = min(delay_ms, 80) if SIMULATION_MODE else delay_ms
                App.after(actual_delay, lambda: notify_slot_ok_received(slot_id))
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
        slot_current_job[slot_id] = None
        if callback:
            callback()
        if slot_current_job[slot_id] is None:
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
                print(f"[+] Slot {i} -> {dev_name} 연결 성공")
            except Exception as e:
                c6Label[i].configure(text='Error', foreground='orange')
                print(f"[!] {dev_name} 연결 오류: {e}")
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
    global portlist, rx_buffers, board_slot_map, sensor_states
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
                            line = line.strip().replace('\r', '')
                            if line:
                                print(f"[RX Slot{i}] {line}")
                                if c6Label[i].winfo_exists():
                                    c6Label[i].configure(text=line[:12], foreground="blue")
                                
                                clean_line = line.replace(" ", "").upper()

                                for b_id in [1, 2]:
                                    if f"READY_{b_id}" in clean_line or f"UNIT{b_id}" in clean_line:
                                        board_slot_map[b_id] = i

                                if i == board_slot_map.get(1, 1):
                                    if "PC7:TRIGGERED" in clean_line:
                                        sensor_states["stm1_pc7"] = "triggered"
                                    elif "PC7:OPEN" in clean_line or "PC7:NOTRIGGER" in clean_line:
                                        sensor_states["stm1_pc7"] = "no trigger"

                                    if "PD2:TRIGGERED" in clean_line:
                                        sensor_states["stm1_pd2"] = "triggered"
                                    elif "PD2:OPEN" in clean_line or "PD2:NOTRIGGER" in clean_line:
                                        sensor_states["stm1_pd2"] = "no trigger"

                                if i == board_slot_map.get(2, 2):
                                    if "PD2:TRIGGERED" in clean_line:
                                        sensor_states["stm2_pd2"] = "triggered"
                                    elif "PD2:OPEN" in clean_line or "PD2:NOTRIGGER" in clean_line or "PD2:IDLE" in clean_line:
                                        sensor_states["stm2_pd2"] = "no trigger"

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
# 6. UI 동기화
# ----------------------------------------------------
STATUS_COLORS = {
    "대기": "gray",
    "1단계:Pick": "#d97706",
    "1단계:완료대기": "#d97706",
    "2단계:Change": "#9333ea",
    "2단계:완료대기": "#9333ea",
    "3단계:CookPlace": "#2563eb",
    "4단계:조리중": "#2563eb",
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
    for i in range(NUM_SLOTS):
        h_id = i + 1
        info = heat_units[h_id]
        btn = slot_dummy_buttons[i]
        if not btn.winfo_exists():
            continue
            
        st = info["status"]
        hp_no = info["plate_id"]
        plate_side = plate_current_side[hp_no]
        side_str = "앞면" if plate_side == "front" else "뒷면"
        remain_s = max(0, int(TIMER_UNIT_STAY_MAX - plate_phase_timer[hp_no]))
        
        if st == "idle":
            btn.configure(
                text=f"조리대 {h_id} (HP{hp_no}-{side_str})\n[비어있음]\n총 00:00\n앞 00:00 | 뒤 00:00\n전환대기: {remain_s//60:02d}:{remain_s%60:02d}",
                bg="#e2e8f0", fg="#64748b", font=("Arial", 7)
            )
        elif st in ["reserved", "cooking"]:
            tot_s = int(info["total_cook_time"])
            f_s = int(info["front_cook_time"])
            b_s = int(info["back_cook_time"])
            
            bg_color = "#16a34a" if plate_side == "front" else "#2563eb"

            display_text = (
                f"조리대 {h_id} (HP{hp_no}-{side_str})\n"
                f"총 {tot_s//60:02d}:{tot_s%60:02d} / 12:00\n"
                f"앞 {f_s//60:02d}:{f_s%60:02d} | 뒤 {b_s//60:02d}:{b_s%60:02d}\n"
                f"전환대기: {remain_s//60:02d}:{remain_s%60:02d}"
            )
            btn.configure(
                text=display_text, bg=bg_color, fg="#ffffff", font=("Arial", 7, "bold")
            )
        elif st == "finished":
            btn.configure(
                text=f"조리대 {h_id} (HP{hp_no}-{side_str})\n[조리완료 배출대기]\n총 12:00 만료\n서빙 대기중",
                bg="#ea580c", fg="#ffffff", font=("Arial", 7, "bold")
            )

# ----------------------------------------------------
# 7. 우선순위 기반 오케스트레이터 (새로운 공정 순서 적용)
# ----------------------------------------------------
def has_cooking_over_limit():
    """요리 조리타이머가 11분 30초(690초)를 초과한 상태 확인"""
    for info in heat_units.values():
        if info["status"] in ["cooking", "finished"] and info["total_cook_time"] >= TIMER_BLOCK_AND_FINISH:
            return True
    return False

def get_ready_stage1_item():
    for item in active_orders:
        if item.get("status") == "1단계:완료대기":
            return item
    return None

def get_empty_heat_slot_in_front_plate():
    """비어있는 조리대 칸 중 앞면 상태이고 위상 반전까지 남은 시간이 20초 이상인 슬롯 탐색"""
    available_plates = [
        p for p in [1, 2] 
        if plate_current_side[p] == "front" and (TIMER_UNIT_STAY_MAX - plate_phase_timer[p]) >= TIMER_STAGE3_MIN_REMAIN
    ]
    for p in available_plates:
        slot_range = range(1, 8) if p == 1 else range(8, 15)
        for s in slot_range:
            if heat_units[s]["status"] == "idle":
                return s
    
    if SIMULATION_MODE:
        for s in range(1, NUM_SLOTS + 1):
            if heat_units[s]["status"] == "idle":
                return s
    return None

def schedule_pipeline():
    """
    개편된 우선순위 처리 오케스트레이터:
    1순위 : 4단계 goto cook (HP1/HP2 상호 반대 위치 유지, 매 2분 주기 교번 회전)
    2순위 : 1단계 pick and place (독립 구동)
    3순위 : 5단계 goto finish (11분 30초 초과 요리 우선 배출)
    4순위 : 2단계 unit change (11분 30초 초과 요리 없을 때 진입 -> 완료 시 PC7 trigger)
    5순위 : 3단계 cook and place (앞면 슬롯 & 남은시간 20초 이상)
    """
    global is_unit1_busy, is_unit2_busy

    while len(active_orders) < NUM_SLOTS and overflow_orders:
        promoted = overflow_orders.pop(0)
        active_orders.append(promoted)
        print(f"[대기열 승격] T{promoted['table']} {promoted['name']}")

    sync_order_queue_ui()
    sync_connection_info_ui()

    # ==========================================
    # [1순위] 4단계: goto cook (최상위 우선순위)
    # 규칙1: HP1과 HP2는 상호 반대
    # 규칙2: 매 2분마다 앞면/뒷면 전환
    # ==========================================
    if not is_unit2_busy and not (plate_flipping_lock[1] or plate_flipping_lock[2]):
        # HP1 또는 HP2 타이머가 2분(120초) 이상 도달 시 둘 다 동시에 맞교대 전환
        if plate_phase_timer[1] >= TIMER_UNIT_STAY_MAX or plate_phase_timer[2] >= TIMER_UNIT_STAY_MAX:
            print("[우선순위 1: 4단계 위상변화] 2분 주기 도달 -> HP1, HP2 상호 반대 교번 회전 실행")
            rotate_both_plates_synchronized()
            return

    # ==========================================
    # [2순위] 1단계: pick and place (독립 구동)
    # 조건1: 주문완료 대기 요리 존재
    # 조건2: stm_unit_1 (PC7, PD2) 센서 no trigger 상태
    # ==========================================
    if not is_unit1_busy:
        c1_pending = None
        for item in active_orders:
            if item["status"] == "대기":
                c1_pending = item
                break

        pc7_ok = SIMULATION_MODE or (sensor_states["stm1_pc7"] == "no trigger")
        pd2_ok = SIMULATION_MODE or (sensor_states["stm1_pd2"] == "no trigger")

        if c1_pending and pc7_ok and pd2_ok:
            _start_stage1_pick(c1_pending)

    # Unit 2가 모션 중이면 3, 4, 5순위 대기
    if is_unit2_busy:
        return

    # ==========================================
    # [3순위] 5단계: goto finish (조리 완료 유닛 신속 배출)
    # 조건1: 조리시간 11분 30초 초과
    # 조건2: stm_unit_1 (PC7) no trigger 상태
    # 조건3: 대상 heat unit의 상태가 앞면
    # 조건4: stm_unit_2가 픽업 전 위치에 위치
    # ==========================================
    finished_candidates = []
    for s_id, info in heat_units.items():
        if info["status"] in ["cooking", "finished"] and info["total_cook_time"] >= TIMER_BLOCK_AND_FINISH:
            finished_candidates.append((s_id, info["total_cook_time"], info["plate_id"]))
    
    if finished_candidates:
        finished_candidates.sort(key=lambda x: x[1], reverse=True)
        for s_id, c_time, p_id in finished_candidates:
            c2_pc7_ok = SIMULATION_MODE or (sensor_states["stm1_pc7"] == "no trigger")
            c3_plate_front = (plate_current_side[p_id] == "front")
            c4_pos_ok = SIMULATION_MODE or unit2_at_prepick_pos

            if c2_pc7_ok and c3_plate_front and c4_pos_ok:
                print(f"[우선순위 3: 5단계 배출] 슬롯 {s_id} (조리시간 {c_time:.1f}초, HP{p_id})")
                _run_stage5_finish(s_id)
                return

    # ==========================================
    # [4순위] 2단계: unit change
    # 조건1: 11분 30초 초과 요리가 없을 것
    # 조건2: stm_unit_1 (PD2) trigger, (PC7) no trigger
    # 조건3: 1단계 완료대기 상태일 것
    # ==========================================
    stage1_done_item = get_ready_stage1_item()
    if stage1_done_item is not None:
        block_by_limit = has_cooking_over_limit() if not SIMULATION_MODE else False
        pd2_trig = SIMULATION_MODE or (sensor_states["stm1_pd2"] == "triggered")
        pc7_notrig = SIMULATION_MODE or (sensor_states["stm1_pc7"] == "no trigger")

        if not block_by_limit and pd2_trig and pc7_notrig:
            print(f"[우선순위 4: 2단계 이송] T{stage1_done_item['table']} {stage1_done_item['name']}")
            _run_stage2_unit_change(stage1_done_item)
            return

    # ==========================================
    # [5순위] 3단계: cook and place
    # 조건1: 11분 30초 초과 요리가 없을 것
    # 조건2: stm_unit_1 (PC7) trigger 상태
    # 조건3: 비어있는 조리대 칸이 앞면 상태일 것
    # 조건4: 상태 변화(2분 만료)까지 남은 시간이 20초 이상일 것
    # ==========================================
    placing_item = None
    for item in active_orders:
        if item.get("status") == "2단계:완료대기":
            placing_item = item
            break

    if placing_item:
        c1_no_limit = not has_cooking_over_limit() if not SIMULATION_MODE else True
        c2_pc7_trig = SIMULATION_MODE or (sensor_states["stm1_pc7"] == "triggered")
        target_slot = get_empty_heat_slot_in_front_plate()

        if c1_no_limit and c2_pc7_trig and (target_slot is not None):
            print(f"[우선순위 5: 3단계 안착] T{placing_item['table']} -> 앞면 슬롯 {target_slot} (20초 이상 확보)")
            _run_stage3_cook_and_place(placing_item, target_slot)
            return

# ----------------------------------------------------
# 8. 세부 공정 실행 루틴 (1 ~ 5단계)
# ----------------------------------------------------
def _start_stage1_pick(item):
    """1단계: Pick and place (stm_unit_1 단독 구동)"""
    global is_unit1_busy
    is_unit1_busy = True
    unit1_slot = board_slot_map.get(1, 1)

    item["status"] = "1단계:Pick"
    sync_order_queue_ui()
    print(f"\n▶ [1단계 시작: Pick] T{item['table']} {item['name']}")

    gcode_list = get_stage1_pick_gcode(item["name"])
    x_map = {"닭고기": 2000, "목살": 2500, "삼겹살": 3000, "양념": 3500}
    b1_x = x_map.get(item["name"], 2000)
    item["b1_x"] = b1_x

    def _on_stage1_done():
        global is_unit1_busy
        is_unit1_busy = False
        item["status"] = "1단계:완료대기"
        
        # 하드웨어 동작 모사: 1단계 완료 시 도킹 구역 도착(PD2 triggered, PC7 no trigger)
        if SIMULATION_MODE:
            sensor_states["stm1_pd2"] = "triggered"
            sensor_states["stm1_pc7"] = "no trigger"

        print(f"[1단계 완료: 대기] T{item['table']} {item['name']} -> 2단계 이송 대기")
        sync_order_queue_ui()
        schedule_pipeline()

    execute_gcode_sequence(unit1_slot, gcode_list, on_done=_on_stage1_done)

def _run_stage2_unit_change(item):
    """2단계: Unit change (결과: stm_unit_1 PC7 trigger)"""
    global is_unit2_busy, unit2_at_prepick_pos
    is_unit2_busy = True
    unit2_at_prepick_pos = False

    unit1_slot = board_slot_map.get(1, 1)
    unit2_slot = board_slot_map.get(2, 2)

    item["status"] = "2단계:Change"
    sync_order_queue_ui()
    b1_x = item.get("b1_x", 2000)

    # 1) Unit 2 접근
    u2_approach = get_stage2_unit2_approach_gcode(b1_x)

    def _step2_dock_unit1():
        execute_gcode_sequence(unit1_slot, GCODE_STAGE2_UNIT1_DOCK, on_done=_step2_grip_unit2)

    def _step2_grip_unit2():
        execute_gcode_sequence(unit2_slot, GCODE_STAGE2_UNIT2_GRIP, on_done=_step2_release_unit1)

    def _step2_release_unit1():
        def _on_u1_released():
            global is_unit2_busy
            print("[2단계 완료] stm_unit_1 복귀 완료 -> stm_unit_1(PC7) 센서 triggered 변화")
            sensor_states["stm1_pc7"] = "triggered"
            item["status"] = "2단계:완료대기"
            is_unit2_busy = False
            sync_order_queue_ui()
            schedule_pipeline()

        execute_gcode_sequence(unit1_slot, GCODE_STAGE2_UNIT1_RELEASE, on_done=_on_u1_released)

    execute_gcode_sequence(unit2_slot, u2_approach, on_done=_step2_dock_unit1)

def _run_stage3_cook_and_place(item, target_slot):
    """3단계: Cook and place"""
    global is_unit2_busy, unit2_at_prepick_pos
    is_unit2_busy = True
    unit2_at_prepick_pos = False

    unit2_slot = board_slot_map.get(2, 2)
    plate_no = heat_units[target_slot]["plate_id"]
    item["assigned_slot"] = target_slot
    item["status"] = "3단계:CookPlace"
    heat_units[target_slot]["status"] = "reserved"

    sync_order_queue_ui()
    sync_heat_units_ui()
    print(f"\n▶ [3단계 시작: Cook and place] 슬롯 {target_slot} (HP{plate_no}) 안착")

    gcode_place = get_stage3_cook_place_gcode(target_slot)

    def _on_placed():
        global is_unit2_busy, unit2_at_prepick_pos
        is_unit2_busy = False
        unit2_at_prepick_pos = True
        
        # 3단계 완료 후 PC7 센서는 다시 no trigger로 복귀
        sensor_states["stm1_pc7"] = "no trigger"

        now = time.time()
        item["status"] = "4단계:조리중"
        heat_units[target_slot]["status"] = "cooking"
        heat_units[target_slot]["order"] = item
        heat_units[target_slot]["total_cook_time"] = 0.0
        heat_units[target_slot]["front_cook_time"] = 0.0
        heat_units[target_slot]["back_cook_time"] = 0.0
        heat_units[target_slot]["heat_unit_stay_time"] = 0.0
        heat_units[target_slot]["total_process_time"] = 0.0
        heat_units[target_slot]["last_tick"] = now

        print(f"[3단계 완료] 조리대 {target_slot} 안착 완료 -> 4단계 조리 및 5종 타이머 가동")
        sync_order_queue_ui()
        sync_heat_units_ui()
        schedule_pipeline()

    execute_gcode_sequence(unit2_slot, gcode_place, on_done=_on_placed)

def rotate_both_plates_synchronized():
    """4단계: HP1과 HP2 상호 반대 상태 동시 맞교대 회전 (규칙 1 & 규칙 2)"""
    global is_unit2_busy
    is_unit2_busy = True
    plate_flipping_lock[1] = True
    plate_flipping_lock[2] = True
    unit2_slot = board_slot_map.get(2, 2)

    to_side_1 = "back" if plate_current_side[1] == "front" else "front"
    to_side_2 = "front" if to_side_1 == "back" else "back"

    flip_gcodes_hp1 = get_stage4_flip_gcode(1, to_side_1)
    flip_gcodes_hp2 = get_stage4_flip_gcode(2, to_side_2)
    combined_gcodes = flip_gcodes_hp1 + flip_gcodes_hp2

    def _done_both_flips():
        global is_unit2_busy
        is_unit2_busy = False
        plate_flipping_lock[1] = False
        plate_flipping_lock[2] = False

        plate_current_side[1] = to_side_1
        plate_current_side[2] = to_side_2
        plate_phase_timer[1] = 0.0
        plate_phase_timer[2] = 0.0

        now = time.time()
        for s in range(1, NUM_SLOTS + 1):
            if heat_units[s]["status"] == "cooking":
                heat_units[s]["heat_unit_stay_time"] = 0.0
                heat_units[s]["last_tick"] = now

        print(f"▶ [4단계 위상변화 완료] HP1 -> {to_side_1} | HP2 -> {to_side_2} (교번 반전 완료)")
        sync_heat_units_ui()
        schedule_pipeline()

    execute_gcode_sequence(unit2_slot, combined_gcodes, on_done=_done_both_flips)

def _run_stage5_finish(slot_id):
    """5단계: Goto finish 배출 (조리시간 11분 30초 초과 요리)"""
    global is_unit2_busy, unit2_at_prepick_pos
    is_unit2_busy = True
    unit2_at_prepick_pos = False
    unit2_slot = board_slot_map.get(2, 2)

    info = heat_units[slot_id]
    info["status"] = "finished"
    if info["order"]:
        info["order"]["status"] = "5단계:완성배출"

    sync_order_queue_ui()
    sync_heat_units_ui()
    print(f"\n▶ [5단계 시작: Finish] 슬롯 {slot_id} 서빙 배출 G-code 송출")

    finish_gcodes = get_stage5_finish_gcode(slot_id)

    def _done_finish():
        global is_unit2_busy, unit2_at_prepick_pos
        is_unit2_busy = False
        unit2_at_prepick_pos = True

        target_order = heat_units[slot_id]["order"]
        if target_order and target_order in active_orders:
            active_orders.remove(target_order)
            print(f"[서빙 완료] T{target_order['table']} {target_order['name']}")

        heat_units[slot_id]["status"] = "idle"
        heat_units[slot_id]["order"] = None
        heat_units[slot_id]["total_cook_time"] = 0.0
        heat_units[slot_id]["front_cook_time"] = 0.0
        heat_units[slot_id]["back_cook_time"] = 0.0
        heat_units[slot_id]["heat_unit_stay_time"] = 0.0
        heat_units[slot_id]["total_process_time"] = 0.0

        sync_order_queue_ui()
        sync_heat_units_ui()
        schedule_pipeline()

    execute_gcode_sequence(unit2_slot, finish_gcodes, on_done=_done_finish)

# ----------------------------------------------------
# 9. 타이머 업데이트 엔진 (0.5초 주기)
# ----------------------------------------------------
def process_cooking_timer_tick():
    global plate_last_tick
    if not is_running or not App.winfo_exists():
        return

    now = time.time()
    dt_plate = now - plate_last_tick
    plate_last_tick = now

    # 플레이트별 2분 체류 타이머 적산
    plate_phase_timer[1] += dt_plate
    plate_phase_timer[2] += dt_plate

    for h_id in range(1, NUM_SLOTS + 1):
        info = heat_units[h_id]
        if info["status"] == "cooking":
            dt = now - (info["last_tick"] if info["last_tick"] > 0 else now)
            info["last_tick"] = now
            
            p_id = info["plate_id"]
            side = plate_current_side[p_id]

            info["total_cook_time"] += dt
            info["heat_unit_stay_time"] += dt
            info["total_process_time"] += dt

            if side == "front":
                info["front_cook_time"] += dt
            else:
                info["back_cook_time"] += dt

    sync_heat_units_ui()
    schedule_pipeline()

    if is_running and App.winfo_exists():
        App.after(500, process_cooking_timer_tick)

# ----------------------------------------------------
# 10. 주문 접수 및 테이블 관리
# ----------------------------------------------------
def cancel_pending_orders_by_table(table_num):
    global active_orders, overflow_orders, table_orders

    t_idx = table_num - 1
    canceled_orders = []

    new_active = []
    for item in active_orders:
        if item.get("table") == table_num and item.get("status") == "대기":
            canceled_orders.append(item)
        else:
            new_active.append(item)
    active_orders = new_active

    new_overflow = []
    for item in overflow_orders:
        if item.get("table") == table_num:
            canceled_orders.append(item)
        else:
            new_overflow.append(item)
    overflow_orders = new_overflow

    if not canceled_orders:
        print(f"[{table_num}번 테이블] 취소 가능한 대기 주문이 없습니다.")
        return

    for item in canceled_orders:
        m_name = item["name"]
        if 0 <= t_idx < len(table_orders):
            if table_orders[t_idx]["count"] > 0:
                table_orders[t_idx]["count"] -= 1
            if table_orders[t_idx]["amount"] >= MENU_PRICE:
                table_orders[t_idx]["amount"] -= MENU_PRICE
            if table_orders[t_idx]["items"].get(m_name, 0) > 0:
                table_orders[t_idx]["items"][m_name] -= 1

    print(f"[{table_num}번 테이블 취소] 대기 주문 {len(canceled_orders)}건 취소 완료")
    update_table_ui(t_idx)
    sync_order_queue_ui()
    sync_connection_info_ui()
    schedule_pipeline()

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
        print(f"[{t_num}테이블 접수] 총 {total_order_cnt}건")

        ordered_items = []
        for m_idx, count in enumerate(menu_counter):
            for _ in range(count):
                ordered_items.append({
                    "table": t_num,
                    "name": MENU_NAMES[m_idx],
                    "status": "대기",
                    "total_order": total_order_cnt,
                    "assigned_slot": None,
                    "b1_x": 2000
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
# 11. 백그라운드 리소스 모니터링
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
        f"[MODE] {'SIMULATION' if SIMULATION_MODE else 'HARDWARE SERIAL'}"
    )

    if sys_status_label.winfo_exists():
        sys_status_label.config(text=status_str)

    if is_running and App.winfo_exists():
        App.after(1000, update_system_statusbar)

# ----------------------------------------------------
# 12. Tkinter GUI 레이아웃
# ----------------------------------------------------
App = tk.Tk()
App.title('Food Automation Orchestrator - Production 12min Architecture')
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

slot_btn_panel = tk.LabelFrame(content_frame, text="가상 조리대 (1~14)", padx=4, pady=4)
slot_btn_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 5), pady=5)

slot_dummy_buttons.clear()
for i in range(14):
    slot_btn_panel.rowconfigure(i, weight=1)
    hp_no = 1 if i < 7 else 2
    init_side = "앞면" if plate_current_side[hp_no] == "front" else "뒷면"
    btn = tk.Button(
        slot_btn_panel,
        text=f"조리대 {i+1} (HP{hp_no}-{init_side})\n[비어있음]\n총 00:00\n앞 00:00 | 뒤 00:00\n전환대기: 02:00",
        font=("Arial", 7),
        bg="#e2e8f0",
        fg="#64748b",
        relief="groove",
        width=20
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
myLF2 = tk.LabelFrame(left_main_panel, text='5-Stage Pipeline Status', padx=2, pady=1, labelanchor='n')
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

# 메뉴 버튼
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

# 테이블 주문 버튼
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

# 테이블별 대기 주문 취소 버튼
cancel_btn_frame = tk.Frame(left_main_panel, pady=2)
cancel_btn_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=5, pady=2)

cancel_table_buttons.clear()
for i in range(5):
    cancel_btn_frame.columnconfigure(i, weight=1)
    t_num = i + 1
    btn = tk.Button(
        cancel_btn_frame,
        text=f"T{t_num} 대기취소",
        bg="#fee2e2",
        fg="#b91c1c",
        font=("Arial", 8, "bold"),
        height=2,
        command=lambda num=t_num: cancel_pending_orders_by_table(num)
    )
    btn.grid(row=0, column=i, padx=2, sticky="ew")
    cancel_table_buttons.append(btn)

# 테이블 상세 내역
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

# 콘솔 모니터링
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

# 우측 카메라 패널
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

# 우측 비전 분석 패널
analysis_panel.rowconfigure(0, weight=1)
analysis_panel.rowconfigure(1, weight=1)
analysis_panel.rowconfigure(2, weight=1)
analysis_panel.columnconfigure(0, weight=1)

analysis_titles = ["Vision #1 상태 분석", "Vision #2 상태 분석", "Vision #3 상태 분석"]
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

# Ollama AI Assistant UI
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
chat_history.insert(tk.END, "[시스템] 12분 조리/2분 위상반전 실전 오케스트레이터 가동.\n", "sys")
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
        mock_reply = f"명령 '{user_text}'을(를) 확인했습니다. 정상 동작 중입니다."
        if is_running and App.winfo_exists():
            App.after(0, lambda: append_chat_message('bot', mock_reply))

    threading.Thread(target=_async_ollama_mock, daemon=True).start()

chat_entry.bind('<Return>', lambda e: send_chat_message())

chat_btn_box = tk.Frame(chat_input_frame)
chat_btn_box.grid(row=0, column=1)

chat_send_btn = tk.Button(chat_btn_box, text="전송", bg="#3b82f6", fg="white", font=("Arial", 9, "bold"), command=send_chat_message)
chat_send_btn.pack(side="left", padx=1)

# 상태바
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

    sync_menu_counter_ui()
    sync_order_queue_ui()
    sync_connection_info_ui()
    
    for i in range(5):
        update_table_ui(i)
    
    App.protocol("WM_DELETE_WINDOW", on_closing)
    App.after(100, serialTester)
    App.after(300, update_system_statusbar)
    App.after(500, process_cooking_timer_tick)
    App.mainloop()