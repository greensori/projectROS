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
from PIL import Image, ImageTk

# 시스템 모니터링 라이브러리
import psutil

try:
    import pynvml
    pynvml.nvmlInit()
    HAS_NVML = True
except Exception:
    HAS_NVML = False
    
'''
### 입력 unit 1 관련 설명

[시스템 핀 맵 및 제어 명세 - 수정 완료본]
디버그 고정: PA13(SWDIO), PA14(SWCLK), PB3(SWO), PB4(NJTRST), PC14/PC15(사용지양)
보드 기본: PA5(LED), PC13(스위치 B1)

[TIM2 메인 3축 선형 보간]
STEP: X(PA0), Y(PA1), Z(PB10)
DIR : X(PC0), Y(PC1), Z(PA8)   <-- PC2에서 PA8로 변경
LIMIT/PROBE:
 - Z_PROBE: PD2 (근접 센서)
 - Z_LIMIT: PB13 (Active-Low)
 - X_LIMIT: PB14 (Active-Low)
 - Y_LIMIT: PB15 (Active-Low)

[TIM3 4개 채널 독립 구동]
STEP: CH1(PA6), CH2(PA7), CH3(PB0), CH4(PB1)
DIR : CH1(PB5), CH2(PB6), CH3(PB7), CH4(PB8)
LIMIT:
 - CH1: PA9
 - CH2: PA10
 - CH3: PA11
 - CH4: PA12
[공압 유닛 (8채널 출력)]
P0: PA4  (로드리스 전진)
P1: PC2  (로드리스 후진)       <-- PA8에서 PC2로 변경
P2: PB2  (TIM3 테이블 그리퍼 1)
P3: PC3  (TIM3 테이블 그리퍼 2)
P4: PC9  (Z축 엔드 그리퍼 1)
P5: PC10 (Z축 엔드 그리퍼 2)
P6: PC11 (TIM3 테이블 리프트 1)
P7: PC12 (TIM3 테이블 리프트 2)
[기타 입력 센서]
PC4: UPPER_SENS_1 (이송 상단 센서 1)
PC5: UPPER_SENS_2 (이송 상단 센서 2)
PC6: REF_SENS_1   (광축 기준 센서 1)
PC7: REF_SENS_2   (광축 기준 센서 2)
PC8: TABLE_LIMIT  (조리 테이블 감지 센서 / 물건 감지 트리거)



### 입력 unit 2 관련 설명

[시스템 핀 맵 및 제어 명세 - 수정 완료본]
디버그 고정: PA13(SWDIO), PA14(SWCLK), PB3(SWO), PB4(NJTRST), PC14/PC15(사용지양)
보드 기본: PA5(LED), PC13(스위치 B1)

[TIM2 메인 3축 선형 보간]
STEP: X(PA0), Y(PA1), Z(PB10)
DIR : X(PC0), Y(PC1), Z(PA8)
LIMIT/PROBE:
 - Z_PROBE: PD2 (근접 센서)
 - Z_LIMIT: PB13 (Active-Low)
 - X_LIMIT: PB14 (Active-Low)
 - Y_LIMIT: PB15 (Active-Low)

[TIM3 4개 채널 독립 구동]
STEP: CH1(PA6), CH2(PA7), CH3(PB0), CH4(PB1)
DIR : CH1(PB5), CH2(PB6), CH3(PB7), CH4(PB8)
LIMIT:
 - CH1: PA9
 - CH2: PA10
 - CH3: PA11
 - CH4: PA12
[공압 유닛 (8채널 출력)]
P0: PA4  (점화유닛 1)
P1: PC2  (점화유닛 2)
P2: PB2  (cooker1_pneu_1)
P3: PC3  (cooker2_pneu_1)
P4: PC9  (미지정)
P5: PC10 (미지정)
P6: PC11 (미지정)
P7: PC12 (미지정)
[기타 입력 센서]
PC4: cooker_1_SENS_1 (조리유닛1 보조센서 1)
PC5: cooker_2_SENS_1 (조리유닛2 보조센서 1)
PC6: REF_SENS_1   (광축 기준 센서 1)
PC7: REF_SENS_2   (광축 기준 센서 2)
PC8: TABLE_LIMIT  (조리 테이블 감지 센서 / 물건 감지 트리거)





'''

# ----------------------------------------------------
# 1. 3단계 G-code 시퀀스 정의
# ----------------------------------------------------
AXIS_GCODES = [
    "G91",
    "G1 X1000 F1200",
    "G1 X100 F600",
    "G1 Z2000 F800",
    "G1 Y1500 F1200"
]

RECIPE_GCODES = {
    "닭고기": [
        "G91",
        "M103 P3 S2000 F1200 D0",
        "G1 Z-2000 F800",
        "M42 P4 S1",
        "M42 P5 S1"
    ],
    "목살": [
        "G91",
        "G1 Z-1500 F800",
        "M42 P2 S1",
        "M103 P1 S1600 F1200 D0",
        "M42 P2 S0"
    ],
    "삼겹살": [
        "G91",
        "G1 Z-2000 F800",
        "M42 P6 S1",
        "M103 P2 S2000 F1500 D0",
        "M42 P6 S0"
    ],
    "양념": [
        "G91",
        "M103 P3 S1500 F1200 D0",
        "M42 P0 S1",
        "M42 P0 S0"
    ]
}

BOARD_SYNC_GCODES = [
    "G91",
    "G1 Z0 F800",
    "G1 Y3000 F1200",
    "G1 Z-1000 F800",
    "M42 P4 S0",
    "M42 P5 S0"
]

MENU_NAMES = ["닭고기", "목살", "삼겹살", "양념"]
MENU_PRICE = 6000

menu_counter = [0, 0, 0, 0]
menu_buttons = []

# 테이블별 누적 주문 관리
table_orders = [{"count": 0, "amount": 0, "items": {name: 0 for name in MENU_NAMES}} for _ in range(5)]
table_buttons = []
table_order_detail_labels = []

dummy_buttons = []

NUM_SLOTS = 14

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
board_slot_map = {}

slot_queues = {i: deque() for i in range(1, NUM_SLOTS + 1)}
slot_current_job = {i: None for i in range(1, NUM_SLOTS + 1)}

# 신규: 카메라 좌측 더미 버튼 참조 리스트
slot_dummy_buttons = []

cam_display_labels = []
cam_photo_images = [None, None, None]

analysis_buttons = [[], [], []]

is_running = True
orig_stdout = sys.stdout
orig_stderr = sys.stderr

current_sys_metrics = {
    "cpu": 0.0,
    "ram_pct": 0.0,
    "ram_used_gb": 0.0,
    "ram_total_gb": 0.0,
    "gpu_load": "N/A",
    "vram_used": "N/A"
}

# ----------------------------------------------------
# 2. 콘솔 출력 리다이렉터
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
# 3. 비동기 큐잉 G-code 엔진
# ----------------------------------------------------
def execute_gcode_sequence(slot_id, gcodes, on_done=None):
    if not (1 <= slot_id <= NUM_SLOTS):
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
        job["waiting_ok"] = True
        send_slot_command(slot_id, cmd)
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
            App.after(10, lambda: _send_job_line(slot_id))

# ----------------------------------------------------
# 4. 시리얼 통신 핵심 함수
# ----------------------------------------------------
def autoDetectAndConnect():
    global portlist, port_names, board_slot_map
    board_slot_map.clear()
    detected = [p.device for p in serial.tools.list_ports.comports()]
    print(f"[시스템] 발견된 포트: {detected}")

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
                print(f"[!] {dev_name} 오픈 실패: {e}")
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

def serialDisconnectAll():
    global portlist, board_slot_map
    board_slot_map.clear()
    print("[시스템] 모든 시리얼 연결 해제")
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

                                for b_id in [1, 2, 3]:
                                    if f"READY_{b_id}" in clean_line or f"READY!{b_id}" in clean_line:
                                        board_slot_map[b_id] = i
                                        print(f"[동기화 감지] STM32 보드 {b_id}번 -> Slot {i} 매핑 완료")

                                if clean_line == "OK" or clean_line.endswith("OK"):
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
                print(f"[!] Slot {slot_id} 송신 실패: {e}")
                return False
    print(f"[!] Slot {slot_id} 포트 미연결: {gcode}")
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
# 5. Order Queue & Pipeline
# ----------------------------------------------------
active_orders = []      
overflow_orders = []    

is_transferring = False  
discharge_queue = deque() 
is_discharging = False   

STATUS_COLORS = {
    "대기": "gray",
    "이송중": "#d97706",
    "조리중": "#2563eb",
    "완성": "#16a34a",
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
    print(f"[담기] {MENU_NAMES[idx]}: 현재 {menu_counter[idx]}개")

def reset_menu_count():
    global menu_counter
    menu_counter = [0, 0, 0, 0]
    sync_menu_counter_ui()
    print("[초기화] 선택된 메뉴 수량이 0으로 초기화되었습니다.")

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
        print(f"[{t_num}테이블 주문 접수] 총 {total_order_cnt}개 메뉴 (+{added_amount:,}원)")

        ordered_items = []
        for m_idx, count in enumerate(menu_counter):
            for _ in range(count):
                ordered_items.append({
                    "table": t_num,
                    "name": MENU_NAMES[m_idx],
                    "status": "대기",
                    "total_order": total_order_cnt
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
            print(f"[{t_idx + 1}테이블 정산 완료] {table_orders[t_idx]['count']}개 / {table_orders[t_idx]['amount']:,}원 초기화")
            table_orders[t_idx]["count"] = 0
            table_orders[t_idx]["amount"] = 0
            table_orders[t_idx]["items"] = {name: 0 for name in MENU_NAMES}
            update_table_ui(t_idx)
        else:
            print(f"[{t_idx + 1}테이블] 정산할 주문 내역이 없습니다.")

def schedule_pipeline():
    global is_transferring
    target_slot = board_slot_map.get(1, 1)

    while len(active_orders) < NUM_SLOTS and overflow_orders:
        promoted_item = overflow_orders.pop(0)
        active_orders.append(promoted_item)
        print(f"[대기열 승격] T{promoted_item['table']} {promoted_item['name']} -> 활성 큐(LF2) 진입")

    sync_order_queue_ui()
    sync_connection_info_ui()

    if not is_transferring and not is_discharging:
        pending_item = None
        for item in active_orders:
            if item["status"] == "대기":
                pending_item = item
                break

        if pending_item:
            is_transferring = True
            pending_item["status"] = "이송중"
            sync_order_queue_ui()
            print(f"\n[1단계 이송 시작] T{pending_item['table']} {pending_item['name']}")

            execute_gcode_sequence(
                slot_id=target_slot,
                gcodes=AXIS_GCODES,
                on_done=lambda target=pending_item: start_cooking_phase(target)
            )

def start_cooking_phase(item):
    global is_transferring
    target_slot = board_slot_map.get(1, 1)

    item["status"] = "조리중"
    sync_order_queue_ui()
    print(f"\n[2단계 조리 진입] T{item['table']} {item['name']} (이송 락 해제)")

    is_transferring = False
    schedule_pipeline()

    recipe = RECIPE_GCODES.get(item["name"], ["G4 P500"])
    execute_gcode_sequence(
        slot_id=target_slot,
        gcodes=recipe,
        on_done=lambda target=item: start_finishing_phase(target)
    )

def start_finishing_phase(item):
    item["status"] = "완성"
    sync_order_queue_ui()
    print(f"\n[3단계 완성] T{item['table']} {item['name']} (배출 큐 등록)")

    discharge_queue.append(item)
    process_discharge_queue()

def process_discharge_queue():
    global is_discharging
    if is_discharging or not discharge_queue:
        return

    if is_transferring:
        if is_running and App.winfo_exists():
            App.after(100, process_discharge_queue)
        return

    is_discharging = True
    target_item = discharge_queue.popleft()
    target_slot = board_slot_map.get(1, 1)

    print(f"[배출 시작] T{target_item['table']} {target_item['name']}")
    execute_gcode_sequence(
        slot_id=target_slot,
        gcodes=BOARD_SYNC_GCODES,
        on_done=lambda target=target_item: complete_order(target)
    )

def complete_order(item):
    global is_discharging
    print(f"[조리/배출 완료] T{item['table']} {item['name']}")
    
    is_discharging = False

    def _remove():
        if item in active_orders:
            active_orders.remove(item)
            sync_order_queue_ui()
            process_discharge_queue()
            schedule_pipeline()

    if is_running and App.winfo_exists():
        App.after(800, _remove)

# ----------------------------------------------------
# 6. 시스템 리소스 모니터링 스레드 및 UI 갱신
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
                    gpu_load_str = "N/A"
                    vram_str = "N/A"

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
        f"[GPU VRAM] {vram_used}"
    )

    if sys_status_label.winfo_exists():
        sys_status_label.config(text=status_str)
    
    if is_running and App.winfo_exists():
        App.after(1000, update_system_statusbar)

# ----------------------------------------------------
# 7. GUI 레이아웃 구성
# ----------------------------------------------------
App = tk.Tk()
App.title('Food Automation & Multi-Camera Vision Controller')
App.resizable(width=True, height=True)
App.geometry('1920x860+40+30')

App.columnconfigure(0, weight=1)
App.rowconfigure(0, weight=1)
App.rowconfigure(1, weight=0)

content_frame = tk.Frame(App)
content_frame.grid(row=0, column=0, sticky="nsew")

# 5개 패널 컬럼 비율 설정: 메인(5) : 세로버튼열(고정) : 카메라(3) : 센서분석(3) : AI챗(3)
content_frame.columnconfigure(0, weight=5)
content_frame.columnconfigure(1, weight=0)
content_frame.columnconfigure(2, weight=3)
content_frame.columnconfigure(3, weight=3)
content_frame.columnconfigure(4, weight=3)
content_frame.rowconfigure(0, weight=1)

left_main_panel = tk.Frame(content_frame)
left_main_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

# --- [신규 추가] 카메라 피드 왼쪽 기능 없는 세로 정렬 버튼 14개 패널 ---
slot_btn_panel = tk.LabelFrame(content_frame, text="슬롯", padx=3, pady=3)
slot_btn_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 5), pady=5)

slot_dummy_buttons.clear()
for i in range(14):
    slot_btn_panel.rowconfigure(i, weight=1)
    btn = tk.Button(
        slot_btn_panel,
        text=f"Slot {i+1}",
        font=("Arial", 8),
        bg="#f8fafc",
        relief="groove"
    )
    btn.grid(row=i, column=0, sticky="nsew", padx=1, pady=1)
    slot_dummy_buttons.append(btn)
# ----------------------------------------------------------------------

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
filemenu.add_command(label='Emergency Stop (M112 비상정지)', command=lambda: send_slot_command(board_slot_map.get(1, 1), "M112"))
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
myLF2 = tk.LabelFrame(left_main_panel, text='Order Queue', padx=2, pady=1, labelanchor='n')
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
myLF3 = tk.LabelFrame(left_main_panel, text='Serial: COM Slots', padx=2, pady=1, labelanchor='n')
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

# 3층: 보조 버튼 영역
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

# 4층: 정산 전 테이블별 주문 상세 내역 표시 패널
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

# 5층: 콘솔 모니터링
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

# ----------------------------------------------------
# 8. 우측 카메라 영역
# ----------------------------------------------------
right_camera_panel.rowconfigure(0, weight=1)
right_camera_panel.rowconfigure(1, weight=1)
right_camera_panel.rowconfigure(2, weight=1)
right_camera_panel.columnconfigure(0, weight=1)

cam_titles = ["Camera Feed 1 (메인 관측)", "Camera Feed 2 (보조 관측)", "Camera Feed 3 (분석/대기)"]

for idx, title in enumerate(cam_titles):
    cam_lf = tk.LabelFrame(right_camera_panel, text=title, padx=5, pady=5)
    cam_lf.grid(row=idx, column=0, sticky="nsew", padx=3, pady=3)
    
    disp_lbl = tk.Label(cam_lf, text=f"CAM {idx+1}\n(No Signal)", bg="#111111", fg="#777777", font=("Arial", 12))
    disp_lbl.pack(fill="both", expand=True)
    cam_display_labels.append(disp_lbl)

def update_camera_views():
    if not is_running or not App.winfo_exists():
        return
    App.after(100, update_camera_views)

# ----------------------------------------------------
# 8-1. 우측 비전 분석 패널
# ----------------------------------------------------
analysis_panel.rowconfigure(0, weight=1)
analysis_panel.rowconfigure(1, weight=1)
analysis_panel.rowconfigure(2, weight=1)
analysis_panel.columnconfigure(0, weight=1)

analysis_titles = [
    "Vision #1 위치/센서 분석",
    "Vision #2 위치/센서 분석",
    "Vision #3 위치/센서 분석"
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
        btn_text = f"S{section_idx+1}-P{b_idx+1}\n[대기]"
        btn = tk.Button(
            sec_lf,
            text=btn_text,
            font=("Arial", 8),
            bg="#f1f5f9",
            padx=2,
            pady=2
        )
        btn.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
        analysis_buttons[section_idx].append(btn)

# ----------------------------------------------------
# 8-2. 제일 우측: AI LLM Chat Assistant (Ollama 연동 대비 패널)
# ----------------------------------------------------
chat_panel.rowconfigure(0, weight=1)
chat_panel.columnconfigure(0, weight=1)

chat_lf = tk.LabelFrame(chat_panel, text='Ollama AI Assistant (Chat)', padx=5, pady=5)
chat_lf.grid(row=0, column=0, sticky="nsew")
chat_lf.rowconfigure(0, weight=1)
chat_lf.rowconfigure(1, weight=0)
chat_lf.columnconfigure(0, weight=1)

chat_history = tk.Text(
    chat_lf,
    bg="#0f172a",
    fg="#f8fafc",
    font=("Arial", 9),
    wrap="word",
    state="disabled"
)
chat_history.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

chat_history.tag_config('user', foreground='#38bdf8', font=("Arial", 9, "bold"))
chat_history.tag_config('bot', foreground='#4ade80')
chat_history.tag_config('sys', foreground='#94a3b8', font=("Arial", 8, "italic"))

chat_scroll = ttk.Scrollbar(chat_lf, orient="vertical", command=chat_history.yview)
chat_scroll.grid(row=0, column=1, sticky="ns", pady=(0, 5))
chat_history.configure(yscrollcommand=chat_scroll.set)

chat_history.configure(state='normal')
chat_history.insert(tk.END, "[시스템] Ollama 테스트 채팅 인터페이스 준비 완료.\n", "sys")
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
        time.sleep(0.4)
        mock_reply = f"(테스트 응답) '{user_text}' 입력을 수신했습니다. Ollama 연동 시 답변이 생성됩니다."
        
        if is_running and App.winfo_exists():
            App.after(0, lambda: append_chat_message('bot', mock_reply))

    threading.Thread(target=_async_ollama_mock, daemon=True).start()

chat_entry.bind('<Return>', lambda e: send_chat_message())

chat_btn_box = tk.Frame(chat_input_frame)
chat_btn_box.grid(row=0, column=1)

chat_send_btn = tk.Button(chat_btn_box, text="전송", bg="#3b82f6", fg="white", font=("Arial", 9, "bold"), command=send_chat_message)
chat_send_btn.pack(side="left", padx=1)

def clear_chat_history():
    chat_history.configure(state='normal')
    chat_history.delete('1.0', tk.END)
    chat_history.insert(tk.END, "[시스템] 대화 내용이 초기화되었습니다.\n", "sys")
    chat_history.configure(state='disabled')

chat_clear_btn = tk.Button(chat_btn_box, text="비우기", bg="#e2e8f0", font=("Arial", 8), command=clear_chat_history)
chat_clear_btn.pack(side="left", padx=1)

# ----------------------------------------------------
# 9. 창 최하단 시스템 정보 상태바
# ----------------------------------------------------
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

# ----------------------------------------------------
# 10. 종료 및 실행
# ----------------------------------------------------
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
    App.after(200, update_camera_views)
    App.after(300, update_system_statusbar)
    App.mainloop()