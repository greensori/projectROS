# -*- coding: utf-8 -*-

import io
import sys
import time
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports

# ----------------------------------------------------
# 1. 4축 멀티라인 G-code 시퀀스 및 메뉴별 커맨드 매핑
# ----------------------------------------------------
AXIS_GCODES = {
    "X-Axis": [
        "G21",
        "G91",
        "G1 X10.0 F1200",
        "G1 X20.0 F800",
        "G1 X-5.0 F1500"
    ],
    "Y-Axis": [
        "G91",
        "G1 Y5.0 F1000",
        "G1 Y15.0 F1000",
        "G1 Y-10.0 F600"
    ],
    "Z-Axis": [
        "G91",
        "G1 Z2.0 F300",
        "G1 Z-2.0 F300"
    ],
    "A-Axis": [
        "G91",
        "G1 A30.0 F1500",
        "G1 A60.0 F1500",
        "G1 A-90.0 F2000"
    ]
}

# 메뉴 기본 정보 정의 (0: 닭고기, 1: 목살, 2: 삼겹살, 3: 양념)
MENU_NAMES = ["닭고기", "목살", "삼겹살", "양념"]
# 메뉴별 실행 동작 정의: 'runner'는 4축 시퀀스, 'cmd'는 단일/다중 G-code 전송
MENU_ACTIONS = [
    {"type": "runner", "slot": 1},
    {"type": "cmd",    "slot": 1, "cmd": "G1 Y10 F1000"},
    {"type": "cmd",    "slot": 1, "cmd": "G28"},
    {"type": "cmd",    "slot": 1, "cmd": "G1 X10 F1000"}
]

# 주문 카운터
menu_counter = [0, 0, 0, 0]
menu_buttons = []

portName = ['주문대기'] + ['-'] * 9
initStat = ['세트대기'] + ['-'] * 9
initBuffer = ['조리대기'] + ['-'] * 9

LF2body = ['menuName'] + ['-'] * 9
LF2body_value = ['now?'] + ['0'] * 9

LF3cmos = ['deviceName']
LF3cmos_value = ['Status:??']
LF3cmos_entry = ['Command']

for i in range(1, 10):
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

# 포트 매핑 (최대 9개 슬롯)
portlist = [None] * 10
port_names = [''] * 10
rx_buffers = [''] * 10  # 부분 수신 데이터 버퍼링

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
# 3. 시리얼 통신 핵심 함수 (완료 수정 금지)
# ----------------------------------------------------
def autoDetectAndConnect():
    """감지된 실제 포트를 Slot 1부터 차례로 자동 할당"""
    global portlist, port_names
    detected = [p.device for p in serial.tools.list_ports.comports()]
    print(f"[시스템] 발견된 포트: {detected}")

    for i in range(1, 10):
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
    global portlist
    print("[시스템] 모든 시리얼 연결 해제")
    for i in range(1, 10):
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
    """개행 기반 안전한 버퍼 RX 리더"""
    global portlist, rx_buffers
    if not is_running:
        return

    for i in range(1, 10):
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
            except Exception:
                c6Label[i].configure(text="Error", foreground="red")

    if is_running:
        App.after(40, serialTester)

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
    print(f"[!] Slot {slot_id} 포트 미연결 상태")
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
# 4. 4축 시퀀서 엔진 (콜백 지원)
# ----------------------------------------------------
class SequenceRunner:
    def __init__(self, slot_id=1, line_interval_ms=100, axis_interval_ms=800):
        self.slot_id = slot_id
        self.line_interval_ms = line_interval_ms
        self.axis_interval_ms = axis_interval_ms
        self.axis_queue = []
        self.current_axis_name = ""
        self.current_lines = []
        self.running = False
        self.on_complete_callback = None

    def start(self, on_complete=None):
        if self.running:
            print("[!] 이미 시퀀스가 동작 중입니다.")
            return

        ser = portlist[self.slot_id]
        if ser is None or not ser.is_open:
            print(f"[!] Slot {self.slot_id}이 열려있지 않아 시퀀스를 실행할 수 없습니다.")
            if on_complete:
                on_complete()
            return

        self.on_complete_callback = on_complete
        self.axis_queue = list(AXIS_GCODES.items())
        self.running = True
        print("\n=== 4축 멀티라인 G-code 시퀀스 시작 ===")
        self._next_axis()

    def _next_axis(self):
        if not self.running:
            return

        if not self.axis_queue:
            print("=== 4축 루틴 전송 완료 ===\n")
            self.running = False
            if self.on_complete_callback:
                cb = self.on_complete_callback
                self.on_complete_callback = None
                cb()
            return

        self.current_axis_name, lines = self.axis_queue.pop(0)
        self.current_lines = list(lines)
        print(f"--- [{self.current_axis_name}] 시작 (총 {len(self.current_lines)}줄) ---")
        self._send_next_line()

    def _send_next_line(self):
        if not self.running:
            return

        if self.current_lines:
            line = self.current_lines.pop(0).strip()
            if line and not line.startswith(";"):
                send_slot_command(self.slot_id, line)
            App.after(self.line_interval_ms, self._send_next_line)
        else:
            App.after(self.axis_interval_ms, self._next_axis)

    def stop(self):
        self.running = False
        self.axis_queue.clear()
        self.current_lines.clear()
        self.on_complete_callback = None
        print("[!] 4축 시퀀스가 정지되었습니다.")

seq_runner = SequenceRunner(slot_id=1, line_interval_ms=100, axis_interval_ms=800)

# ----------------------------------------------------
# 5. 주문 큐 및 카운터 관리 로직
# ----------------------------------------------------
def sync_ui():
    """menu_counter 값을 바탕으로 버튼 텍스트 및 LF2 UI 전체 갱신"""
    global menu_counter, menu_buttons, c3Label, c4Label
    
    for idx in range(4):
        if idx < len(menu_buttons):
            menu_buttons[idx].configure(text=f"{MENU_NAMES[idx]} ({menu_counter[idx]})")
        
        ui_slot = idx + 1
        if ui_slot < len(c3Label) and ui_slot < len(c4Label):
            c3Label[ui_slot].configure(text=MENU_NAMES[idx])
            c4Label[ui_slot].configure(text=str(menu_counter[idx]))

def add_menu_count(idx):
    """1~4번 메뉴 클릭 시 카운트 증가"""
    menu_counter[idx] += 1
    sync_ui()
    print(f"[담기] {MENU_NAMES[idx]}: 현재 {menu_counter[idx]}개")

order_execution_queue = []
is_processing_order = False

def start_order_processing():
    """주문 버튼 클릭 시: 누적 카운트 큐 생성 후 1건씩 순차 실행 및 차감"""
    global is_processing_order, order_execution_queue
    
    if is_processing_order:
        print("[!] 이미 주문이 처리 중입니다. 완료 후 다시 시도하세요.")
        return

    if sum(menu_counter) == 0:
        print("[!] 담긴 메뉴가 없습니다. 메뉴 버튼을 먼저 눌러주세요.")
        return

    order_execution_queue.clear()
    for idx, count in enumerate(menu_counter):
        for _ in range(count):
            order_execution_queue.append(idx)

    print(f"\n=== 주문 처리 시작 (총 {len(order_execution_queue)}건) ===")
    is_processing_order = True
    process_next_item()

def process_next_item():
    """큐에서 메뉴를 꺼내 G-code를 보내고 카운트를 1 차감"""
    global is_processing_order, order_execution_queue, menu_counter

    if not order_execution_queue:
        print("=== 모든 주문 처리가 완료되었습니다. ===\n")
        is_processing_order = False
        return

    target_menu_idx = order_execution_queue.pop(0)
    action = MENU_ACTIONS[target_menu_idx]
    m_name = MENU_NAMES[target_menu_idx]

    menu_counter[target_menu_idx] = max(0, menu_counter[target_menu_idx] - 1)
    sync_ui()
    print(f"\n[조리/전송 중] {m_name} (잔여: {menu_counter[target_menu_idx]}개)")

    if action["type"] == "runner":
        seq_runner.start(on_complete=lambda: App.after(500, process_next_item))
    elif action["type"] == "cmd":
        send_slot_command(action["slot"], action["cmd"])
        App.after(500, process_next_item)

# ----------------------------------------------------
# 6. GUI 레이아웃 구성 (변경 금지)
# ----------------------------------------------------
App = tk.Tk()
App.title('Food Automation Controller')
App.resizable(width=False, height=False)
App.geometry('750x620+400+150')

App.rowconfigure(3, weight=1)
App.columnconfigure(0, weight=1)
App.columnconfigure(1, weight=1)
App.columnconfigure(2, weight=1)

topmenu = tk.Menu(App)
filemenu = tk.Menu(topmenu, tearoff=0)
filemenu.add_command(label='Auto Connect', command=autoDetectAndConnect)
filemenu.add_command(label='Disconnect All', command=serialDisconnectAll)
filemenu.add_separator()
filemenu.add_command(label='Send Entries', command=c7entrySender)
topmenu.add_cascade(label='Port Manager', menu=filemenu)
App.config(menu=topmenu)

# LF1: 연결 상태
myLF1 = tk.LabelFrame(App, text='Connection Info', width=290, height=320, padx=2, pady=2, labelanchor='n')
myLF1.grid_propagate(False)
myLF1.grid(row=0, column=0, padx=10, pady=5)

for count, name in enumerate(portName):
    lbl = tk.Label(myLF1, text=name, padx=4, pady=3)
    lbl.grid(row=count, column=0, sticky='w')
    c0Label.append(lbl)

for count, stat in enumerate(initStat):
    lbl = tk.Label(myLF1, text=stat, padx=4, pady=3)
    lbl.grid(row=count, column=1)
    c1Label.append(lbl)

for count, buff in enumerate(initBuffer):
    lbl = tk.Label(myLF1, text=buff, padx=4, pady=3)
    lbl.grid(row=count, column=2)
    c2Label.append(lbl)

# LF2: 주문 대기열
myLF2 = tk.LabelFrame(App, text='Order Queue', width=160, height=320, padx=2, pady=2, labelanchor='n')
myLF2.grid_propagate(False)
myLF2.grid(row=0, column=1, padx=10, pady=5)

for count, name in enumerate(LF2body):
    lbl = tk.Label(myLF2, text=name, padx=4, pady=3)
    lbl.grid(row=count, column=0)
    c3Label.append(lbl)

for count, val in enumerate(LF2body_value):
    lbl = tk.Label(myLF2, text=val, padx=4, pady=3)
    lbl.grid(row=count, column=1)
    c4Label.append(lbl)

# LF3: 시리얼 슬롯 & 커맨드 입력
myLF3 = tk.LabelFrame(App, text='Serial: COM Slots', width=240, height=320, padx=2, pady=2, labelanchor='n')
myLF3.grid_propagate(False)
myLF3.grid(row=0, column=2, padx=10, pady=5)

for count, dev in enumerate(LF3cmos):
    lbl = tk.Label(myLF3, text=dev, padx=3, pady=3)
    lbl.grid(row=count, column=0)
    c5Label.append(lbl)

for count, stat in enumerate(LF3cmos_value):
    lbl = tk.Label(myLF3, text=stat, padx=3, pady=3)
    lbl.grid(row=count, column=1)
    c6Label.append(lbl)

for count, entry_name in enumerate(LF3cmos_entry):
    if count == 0:
        btn = tk.Button(myLF3, text='전송', width=6, command=c7entrySender)
        btn.grid(row=count, column=2, padx=2, pady=1)
        c7Entry.append(btn)
    else:
        ent = tk.Entry(myLF3, width=8)
        ent.grid(row=count, column=2, padx=2, pady=1)
        ent.bind('<Return>', lambda event, idx=count: (
            send_slot_command(idx, c7Entry[idx].get().strip()),
            c7Entry[idx].delete(0, tk.END)
        ))
        c7Entry.append(ent)

# Mid Frame: 1~4번 메뉴 카운트 버튼 + 5번 주문 전송 버튼
mid_frame = tk.Frame(App, pady=5)
mid_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=5)

button_specs = [
    {"name": "닭고기", "color": "#d9ead3", "is_order_btn": False},
    {"name": "목살",   "color": "#fff2cc", "is_order_btn": False},
    {"name": "삼겹살", "color": "#e2e2e2", "is_order_btn": False},
    {"name": "양념",   "color": "#e0f2fe", "is_order_btn": False},
    {"name": "주문 전송", "color": "#f4cccc", "is_order_btn": True}
]

menu_buttons.clear()

for i, spec in enumerate(button_specs):
    mid_frame.columnconfigure(i, weight=1)
    
    if not spec["is_order_btn"]:
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
            command=start_order_processing
        )
    btn.grid(row=0, column=i, padx=3, sticky="ew")

# 하단 콘솔 모니터링 프레임
console_frame = tk.LabelFrame(App, text='Console Monitoring', padx=5, pady=5)
console_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="nsew")

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

def on_closing():
    global is_running
    is_running = False
    seq_runner.stop()
    serialDisconnectAll()
    sys.stdout = orig_stdout
    sys.stderr = orig_stderr
    App.destroy()

if __name__ == '__main__':
    sync_ui()
    App.protocol("WM_DELETE_WINDOW", on_closing)
    App.after(100, serialTester)
    App.mainloop()