# -*- coding: utf-8 -*-

import io
import sys
import time
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
from PIL import Image, ImageTk  # 카메라 프레임 출력을 위해 필요 (pip install pillow)

# ----------------------------------------------------
# 1. 3단계 G-code 시퀀스 정의
# ----------------------------------------------------
AXIS_GCODES = [
    "G91",
    "G1 X1000 F1200",
    "G38 X30000 F800",
    "G1 X100 F600",
    "G1 Z2000 F800",
    "G1 Y1500 F1200"
]

RECIPE_GCODES = {
    "닭고기": [
        "G91",
        "M103 P3 S2000 F1200 D0",
        "G1 Z-2000 F800",
        "G38 Z-20000 F500",
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
    "G90",
    "G1 Z0 F800",
    "G91",
    "G1 Y3000 F1200",
    "G1 Z-1000 F800",
    "M42 P4 S0",
    "M42 P5 S0"
]

MENU_NAMES = ["닭고기", "목살", "삼겹살", "양념"]
MENU_PRICE = 6000  # 메뉴 단가 6,000원

menu_counter = [0, 0, 0, 0]
menu_buttons = []

# 테이블별 독립 수량 및 금액 관리 (1~5번 테이블)
table_orders = [{"count": 0, "amount": 0} for _ in range(5)]
table_buttons = []

# ====================================================
# 패널별 슬롯 수: 헤더(0번) + 14개 라인 (1~14번)
# ====================================================
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

c0Label = []
c1Label = []
c2Label = []
c3Label = []
c4Label = []
c5Label = []
c6Label = []
c7Entry = []

portlist = [None] * (NUM_SLOTS + 1)
port_names = [''] * (NUM_SLOTS + 1)
rx_buffers = [''] * (NUM_SLOTS + 1)
board_slot_map = {}

# 카메라 뷰어용 위젯 및 참조 리스트
cam_display_labels = []
cam_photo_images = [None, None, None]

is_running = True
orig_stdout = sys.stdout
orig_stderr = sys.stderr

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

        try:
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, string, self.tag)
            
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
# 3. 비동기 G-code 시퀀스 전송 엔진
# ----------------------------------------------------
def execute_gcode_sequence(slot_id, gcodes, line_delay_ms=100, on_done=None):
    lines = [line.strip() for line in gcodes if line.strip() and not line.strip().startswith(";")]

    def _step(idx=0):
        if not is_running:
            return
        if idx < len(lines):
            send_slot_command(slot_id, lines[idx])
            App.after(line_delay_ms, lambda: _step(idx + 1))
        else:
            if on_done:
                on_done()

    _step(0)

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
        if i < len(c6Label):
            c6Label[i].configure(text="DC", foreground="black")

def serialTester():
    global portlist, rx_buffers, board_slot_map
    if not is_running:
        return

    for i in range(1, NUM_SLOTS + 1):
        ser = portlist[i]
        if ser is not None and ser.is_open:
            try:
                waiting = ser.in_waiting
                if waiting > 0:
                    chunk = ser.read(waiting).decode('utf-8', errors='ignore')
                    rx_buffers[i] += chunk
                    
                    while '\n' in rx_buffers[i]:
                        line, rx_buffers[i] = rx_buffers[i].split('\n', 1)
                        line = line.strip()
                        if line:
                            print(f"[RX Slot{i}] {line}")
                            c6Label[i].configure(text=line[:12], foreground="blue")
                            
                            clean_line = line.replace(" ", "").upper()
                            for b_id in [1, 2, 3]:
                                if f"READY_{b_id}" in clean_line or f"READY!{b_id}" in clean_line:
                                    board_slot_map[b_id] = i
                                    print(f"[동기화 감지] STM32 보드 {b_id}번 -> Slot {i} 매핑 완료")
            except Exception:
                c6Label[i].configure(text="Error", foreground="red")

    if is_running:
        App.after(30, serialTester)

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
# 5. Order Queue(LF2) & Connection Info(LF1) 관리
# ----------------------------------------------------
active_orders = []       # Order Queue (LF2): 최대 14개 활성 조리 슬롯
overflow_orders = []     # Connection Info (LF1): 14개 초과 대기열
is_transferring = False  # 1단계(이송중) 단 1개 독점 락

STATUS_COLORS = {
    "대기": "gray",
    "이송중": "#d97706",
    "조리중": "#2563eb",
    "완성": "#16a34a",
    "-": "black"
}

def sync_order_queue_ui():
    """LF2 (Order Queue): 1~14번 슬롯 표출"""
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

        if i < len(c3Label):
            c3Label[i].configure(text=name_text)
        if i < len(c4Label):
            c4Label[i].configure(text=stat_text, fg=color)

def sync_connection_info_ui():
    """LF1 (Connection Info): 14개 초과 조리 메뉴 요약 표출"""
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

        if i < len(c0Label):
            c0Label[i].configure(text=c0_text)
        if i < len(c1Label):
            c1Label[i].configure(text=c1_text)
        if i < len(c2Label):
            c2Label[i].configure(text=c2_text, fg=fg_color)

def sync_menu_counter_ui():
    for idx in range(4):
        if idx < len(menu_buttons):
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
    count = table_orders[t_idx]["count"]
    amt = table_orders[t_idx]["amount"]
    table_buttons[t_idx].configure(text=f"{t_idx + 1}테이블주문 ({count})\n{amt:,}원")

def handle_table_button(t_idx):
    global menu_counter, table_orders
    current_selected_sum = sum(menu_counter)

    if current_selected_sum > 0:
        added_amount = current_selected_sum * MENU_PRICE
        table_orders[t_idx]["count"] += current_selected_sum
        table_orders[t_idx]["amount"] += added_amount
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
            update_table_ui(t_idx)
        else:
            print(f"[{t_idx + 1}테이블] 정산할 주문 내역이 없습니다.")

def schedule_pipeline():
    global is_transferring
    target_slot = board_slot_map.get(1, 1)

    while len(active_orders) < NUM_SLOTS and overflow_orders:
        promoted_item = overflow_orders.pop(0)
        active_orders.append(promoted_item)
        print(f"[대기열 승격] T{promoted_item['table']} {promoted_item['name']} -> 활성 조리 큐(LF2) 진입")

    sync_order_queue_ui()
    sync_connection_info_ui()

    if not is_transferring:
        pending_item = None
        for item in active_orders:
            if item["status"] == "대기":
                pending_item = item
                break

        if pending_item:
            is_transferring = True
            pending_item["status"] = "이송중"
            sync_order_queue_ui()
            print(f"\n[1단계 이송] T{pending_item['table']} {pending_item['name']} (AXIS_GCODES 전송)")

            execute_gcode_sequence(
                slot_id=target_slot,
                gcodes=AXIS_GCODES,
                line_delay_ms=80,
                on_done=lambda it=pending_item: start_cooking_phase(it)
            )

def start_cooking_phase(item):
    global is_transferring
    target_slot = board_slot_map.get(1, 1)

    is_transferring = False
    item["status"] = "조리중"
    sync_order_queue_ui()
    print(f"\n[2단계 조리] T{item['table']} {item['name']} (RECIPE_GCODES 전송)")

    schedule_pipeline()

    recipe = RECIPE_GCODES.get(item["name"], ["G4 P500"])
    execute_gcode_sequence(
        slot_id=target_slot,
        gcodes=recipe,
        line_delay_ms=100,
        on_done=lambda it=item: start_finishing_phase(it)
    )

def start_finishing_phase(item):
    target_slot = board_slot_map.get(1, 1)
    item["status"] = "완성"
    sync_order_queue_ui()
    print(f"\n[3단계 완성] T{item['table']} {item['name']} (BOARD_SYNC_GCODES 전송)")

    execute_gcode_sequence(
        slot_id=target_slot,
        gcodes=BOARD_SYNC_GCODES,
        line_delay_ms=100,
        on_done=lambda it=item: complete_order(it)
    )

def complete_order(item):
    print(f"[조리/배출 완료] T{item['table']} {item['name']}")
    
    def _remove():
        if item in active_orders:
            active_orders.remove(item)
            sync_order_queue_ui()
            schedule_pipeline()

    App.after(1500, _remove)

# ----------------------------------------------------
# 6. GUI 레이아웃 구성 (폰트 및 윈도우 확대 적용)
# ----------------------------------------------------
App = tk.Tk()
App.title('Food Automation & Multi-Camera Vision Controller')
App.resizable(width=True, height=True)
# 14개 행 텍스트 확대를 고려하여 창 해상도를 1366x880으로 여유 있게 설정
App.geometry('1366x880+100+40')

# 최상위 2단 분할
App.columnconfigure(0, weight=6)
App.columnconfigure(1, weight=4)
App.rowconfigure(0, weight=1)

left_main_panel = tk.Frame(App)
left_main_panel.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

right_camera_panel = tk.Frame(App, width=480)
right_camera_panel.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)

# 좌측 메인 패널 그리드 구성
left_main_panel.columnconfigure(0, weight=1)
left_main_panel.columnconfigure(1, weight=1)
left_main_panel.columnconfigure(2, weight=1)
left_main_panel.rowconfigure(4, weight=1)

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

# 공통 폰트 정의 (가독성 향상)
FONT_HEADER = ("맑은 고딕", 11, "bold")
FONT_ROW = ("맑은 고딕", 11)

# LF1: Connection Info (14개 라인, 폰트 11pt 확대)
myLF1 = tk.LabelFrame(left_main_panel, text='Connection Info', padx=4, pady=2, font=("맑은 고딕", 10, "bold"), labelanchor='n')
myLF1.grid(row=0, column=0, padx=4, pady=3, sticky="nsew")

for count, name in enumerate(portName):
    fnt = FONT_HEADER if count == 0 else FONT_ROW
    lbl = tk.Label(myLF1, text=name, padx=4, pady=2, font=fnt)
    lbl.grid(row=count, column=0, sticky='w')
    c0Label.append(lbl)

for count, stat in enumerate(initStat):
    fnt = FONT_HEADER if count == 0 else FONT_ROW
    lbl = tk.Label(myLF1, text=stat, padx=4, pady=2, font=fnt)
    lbl.grid(row=count, column=1)
    c1Label.append(lbl)

for count, buff in enumerate(initBuffer):
    fnt = FONT_HEADER if count == 0 else FONT_ROW
    lbl = tk.Label(myLF1, text=buff, padx=4, pady=2, font=fnt)
    lbl.grid(row=count, column=2)
    c2Label.append(lbl)

# LF2: Order Queue (14개 라인, 폰트 11pt 확대)
myLF2 = tk.LabelFrame(left_main_panel, text='Order Queue', padx=4, pady=2, font=("맑은 고딕", 10, "bold"), labelanchor='n')
myLF2.grid(row=0, column=1, padx=4, pady=3, sticky="nsew")

for count, name in enumerate(LF2body):
    fnt = FONT_HEADER if count == 0 else FONT_ROW
    lbl = tk.Label(myLF2, text=name, padx=4, pady=2, font=fnt)
    lbl.grid(row=count, column=0)
    c3Label.append(lbl)

for count, val in enumerate(LF2body_value):
    fnt = FONT_HEADER if count == 0 else FONT_ROW
    lbl = tk.Label(myLF2, text=val, padx=4, pady=2, font=fnt)
    lbl.grid(row=count, column=1)
    c4Label.append(lbl)

# LF3: Serial: COM Slots (14개 라인, 폰트 11pt 확대)
myLF3 = tk.LabelFrame(left_main_panel, text='Serial: COM Slots', padx=4, pady=2, font=("맑은 고딕", 10, "bold"), labelanchor='n')
myLF3.grid(row=0, column=2, padx=4, pady=3, sticky="nsew")

for count, dev in enumerate(LF3cmos):
    fnt = FONT_HEADER if count == 0 else FONT_ROW
    lbl = tk.Label(myLF3, text=dev, padx=3, pady=2, font=fnt)
    lbl.grid(row=count, column=0)
    c5Label.append(lbl)

for count, stat in enumerate(LF3cmos_value):
    fnt = FONT_HEADER if count == 0 else FONT_ROW
    lbl = tk.Label(myLF3, text=stat, padx=3, pady=2, font=fnt)
    lbl.grid(row=count, column=1)
    c6Label.append(lbl)

for count, entry_name in enumerate(LF3cmos_entry):
    if count == 0:
        btn = tk.Button(myLF3, text='전송', width=6, pady=0, font=("맑은 고딕", 9, "bold"), command=c7entrySender)
        btn.grid(row=count, column=2, padx=2, pady=1)
        c7Entry.append(btn)
    else:
        ent = tk.Entry(myLF3, width=8, font=("맑은 고딕", 10))
        ent.grid(row=count, column=2, padx=2, pady=1)
        ent.bind('<Return>', lambda event, idx=count: (
            send_slot_command(idx, c7Entry[idx].get().strip()),
            c7Entry[idx].delete(0, tk.END)
        ))
        c7Entry.append(ent)

# 1층 버튼: 메뉴 카운트 버튼 + 초기화 버튼 (폰트 11pt Bold 확대)
mid_frame = tk.Frame(left_main_panel, pady=4)
mid_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=4, pady=4)

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
            font=("맑은 고딕", 11, "bold"),
            height=2,
            command=lambda idx=i: add_menu_count(idx)
        )
        menu_buttons.append(btn)
    else:
        btn = tk.Button(
            mid_frame,
            text=spec["name"],
            bg=spec["color"],
            font=("맑은 고딕", 11, "bold"),
            height=2,
            command=reset_menu_count
        )
    btn.grid(row=0, column=i, padx=3, sticky="ew")

# 2층 버튼: 1~5테이블주문 (폰트 11pt Bold 확대)
sub_btn_frame = tk.Frame(left_main_panel, pady=4)
sub_btn_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=4, pady=4)

table_buttons.clear()
for i in range(5):
    sub_btn_frame.columnconfigure(i, weight=1)
    btn = tk.Button(
        sub_btn_frame,
        text=f"{i+1}테이블주문 (0)\n0원",
        bg="#f0f0f0",
        font=("맑은 고딕", 11, "bold"),
        height=2,
        command=lambda idx=i: handle_table_button(idx)
    )
    btn.grid(row=0, column=i, padx=3, sticky="ew")
    table_buttons.append(btn)

# 하단 콘솔 모니터링 프레임 (폰트 확대)
console_frame = tk.LabelFrame(left_main_panel, text='Console Monitoring', padx=6, pady=4, font=("맑은 고딕", 10, "bold"))
console_frame.grid(row=4, column=0, columnspan=3, padx=4, pady=4, sticky="nsew")

font_family = "Courier" if sys.platform == "darwin" else "Consolas"
console_text = tk.Text(
    console_frame,
    height=8,
    bg="#1e1e1e",
    fg="#d4d4d4",
    font=(font_family, 10),
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
# 7. 우측 대형 카메라 뷰어 영역 (3개 화면)
# ----------------------------------------------------
right_camera_panel.rowconfigure(0, weight=1)
right_camera_panel.rowconfigure(1, weight=1)
right_camera_panel.rowconfigure(2, weight=1)
right_camera_panel.columnconfigure(0, weight=1)

cam_titles = ["Camera Feed 1 (메인 관측)", "Camera Feed 2 (보조 관측)", "Camera Feed 3 (분석/대기)"]

for idx, title in enumerate(cam_titles):
    cam_lf = tk.LabelFrame(right_camera_panel, text=title, padx=5, pady=5, font=("맑은 고딕", 10, "bold"))
    cam_lf.grid(row=idx, column=0, sticky="nsew", padx=3, pady=3)
    
    disp_lbl = tk.Label(cam_lf, text=f"CAM {idx+1}\n(No Signal)", bg="#111111", fg="#777777", font=("맑은 고딕", 12))
    disp_lbl.pack(fill="both", expand=True)
    cam_display_labels.append(disp_lbl)

def update_camera_views():
    if not is_running:
        return
    App.after(100, update_camera_views)

# ----------------------------------------------------
# 8. 종료 처리 및 실행
# ----------------------------------------------------
def on_closing():
    global is_running
    is_running = False
    serialDisconnectAll()
    sys.stdout = orig_stdout
    sys.stderr = orig_stderr
    App.destroy()

if __name__ == '__main__':
    sync_menu_counter_ui()
    sync_order_queue_ui()
    sync_connection_info_ui()
    App.protocol("WM_DELETE_WINDOW", on_closing)
    App.after(100, serialTester)
    App.after(200, update_camera_views)
    App.mainloop()