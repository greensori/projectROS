   # -*- coding: utf-8 -*-








import io
import sys
import time
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports



# ----------------------------------------------------
# 1. 4축 멀티라인 G-code 시퀀스 정의 (필요에 맞게 수정)
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




portName = ['portName', 'ttyS0 (UART0)', 'ttyTHS2 (UART1)', 'i2c (master)'
            , 'USB 3.0 (CMOS)', 'USB OTG', 'GPIO (H13)', 'GPIO (G14)'
            , 'GPIO (A22)', 'GPIO (A23)']
initStat = ['status', 'connect', 'connect', 'openDrain', 'connect'
            , 'notin', 'gpio_pq4_pi4', 'can_gpio2_paa2', 'gpio_mdm7_py6', 'gpio_mdm1_py0']
initBuffer = ['bufferSize', '0', '0', '0', '0', '0', '0', '0', '0', '0']


LF2body = ['menuName'] + ['-'] * 9
LF2body_value = ['now?'] + ['0'] * 9


LF3cmos = ['deviceName']
LF3cmos_value = ['Status:??']
LF3cmos_entry = ['Command']

for i in range(1, 10):
    LF3cmos.append('COM%d' %i)
    LF3cmos_value.append('NOTIN%d' %i)
    LF3cmos_entry.append('Enter%d' %i)



c0Label = []
c1Label = []
c2Label = []
c3Label = []
c4Label = []
c5Label = []
c6Label = []
c7Entry = []


# 실제 Serial 객체를 담을 리스트 (인덱스 0은 dummy, 1~9는 포트 슬롯)
port_connected_checker = ['checker'] + ['0'] * 9
portlist = ['portlist']
for i in range(1, 10):
    portlist.append('port%d' %i)
    
    
is_running = True
tester_after_id = None

orig_stdout = sys.stdout
orig_stderr = sys.stderr


##주문에 필요한 객체 리스트 

max_serve = 0   #접시 한개에 담을수 있는 음식 수량으로 최대값은 3
sum_per_order = 0  #한사람이 주문한 음식의 양
dish_serve = 0  #최종적으로 제공되는 음식 변수

process_andgle = 0 # 현재 얼마만큼 돌았는지? 1바퀴 200스텝이라면 이걸 쪼개서 입력하기.. 


order_delay_line = 0 #만약 processor_stage_12 = 1인 경우 여기에 넣기


#기본적으로 process_stage는 등속운동이지만, first_timer에 잔여시간이 있는 경우 신곡하게 
#남은 timer를 반환하고, 5도 까지 신속이동(리미트 스위치 두고 이동 했는지 확인해야...)

## -버튼을 누르는 동작 실행시 

#- max_serve , dish_serve 동시에 ++
#- 냉장고 동작 작동 후 조리기계에 넣을 경우 
#- process_stage_1 ++, 조리축 회전 코드 전송 및 타이머 실행
#- process_stage_12 메뉴추가 혹은 일정시간 경과시 이동하지만,  잔여시간 타이머는 유지되야 함
#-- 각 단계별로 총 조리시간 타이머 와 단계타이머를 만들어서 단계타이머 만료시 다음 단계로 이동
#-- 단계타이머는 초기화, 하지만, 단계타이머 남은 상황에서 조리단계 경과시 단계타이머의 시간 합산

# 1 empty 11full 인경우 전부 뒤로 백해서??

#-- process_stage12에서는 총 조리시간 타이머만 확인...
#-- process_stage1 에 변수 있는 경우 코드 전송 지연... order_delay_line에 저장

# 종결단계에서 타이머0, 그리고 센서작동일 경우 로드리스로 이송 실행

# 중간에 메뉴가 투입될수 있다는 것을 항상 인지하고 있기....
# 한번에 5도가 아닌... 각도를 쪼개서 전송.. 중간에 메뉴가 투입되면, 바로 원점복귀 후 다시 다음 각도로 이동

# 냉장고를 중고로 구입?
#  

# 접시를 미리 준비해서 드랍해야 함.... 접시 보관 냉장고도 추가로 구입해야 
# 
#




# ----------------------------------------------------
# 3. 콘솔 출력 리다이렉터 & 로깅 헬퍼
# ----------------------------------------------------
class ConsoleRedirector:
    def __init__(self, text_widget, original_stream, tag='out', max_lines=50):
        self.text_widget = text_widget
        self.original_stream = original_stream
        self.tag = tag
        self.max_lines = max_lines

    def write(self, string):
        if self.original_stream:
            self.original_stream.write(string)
            self.original_stream.flush()

        # 빈 문자열이나 단독 개행 연속 호출 시 GUI 갱신 스킵
        if not string or not is_running:
            return

        try:
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, string, self.tag)
            
            # 버퍼가 너무 쌓이지 않도록 오래된 줄 삭제
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
# 4. 시리얼 통신 핵심 함수
# ----------------------------------------------------

def autoDetectAndConnect():
    global portlist, port_connected_checker, c6Label
    
    # PC에 현재 꽂혀있는 활성 포트 리스트업
    available_ports = [port.device for port in serial.tools.list_ports.comports()]
    print(f'Available ports: {available_ports}')
    
    for i in range(1, 10):
        port_name = f'COM{i}'
        if port_name in available_ports:
            try:
                portlist[i] = serial.Serial(port_name, 115200, timeout=0.1)
                portlist[i].dtr = False
                portlist[i].rts = False
                portlist[i].reset_input_buffer()
                portlist[i].reset_output_buffer()
                c6Label[i].configure(text='C')
                port_connected_checker[i] = '1'
            except serial.SerialException:
                c6Label[i].configure(text='Busy/Error')
        else:
            c6Label[i].configure(text='DC')
            port_connected_checker[i] = '0'



def get_available_ports():
    """현재 PC에 연결된 모든 시리얼 포트 목록 반환 및 출력"""
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("[!] 연결된 시리얼 포트가 없습니다. USB 연결을 확인하세요.")
        return []
    
    print("=== 현재 연결된 포트 목록 ===")
    for idx, port in enumerate(ports):
        # Mac: /dev/tty.usbmodem... 또는 /dev/tty.usbserial...
        # Windows: COM3, COM4 ...
        print(f"[{idx}] {port.device} - {port.description}")
    return ports


def read_serial_data(port_name, baudrate=115200):
    """지정한 포트에서 시리얼 데이터를 실시간 수신"""
    try:
        # timeout=1: 데이터가 없어도 무한 대기하지 않고 루프 유지
        ser = serial.Serial(port=port_name, baudrate=baudrate, timeout=1)
        print(f"\n[+] {port_name} (Baudrate: {baudrate}) 연결 성공. 수신 대기 중... (종료: Ctrl+C)")
        
        # 버퍼 비우기
        ser.reset_input_buffer()

        while True:
            # 수신 대기 중인 바이트 수가 있는지 확인
            if ser.in_waiting > 0:
                # 줄바꿈(\n) 기준으로 읽기
                raw_data = ser.readline()
                try:
                    # UTF-8 또는 ASCII 디코딩
                    decoded_data = raw_data.decode('utf-8', errors='replace').strip()
                    if decoded_data:
                        print(f"[수신] {decoded_data}")
                except UnicodeDecodeError:
                    print(f"[Raw Hex] {raw_data.hex()}")
            
            time.sleep(0.01) # CPU 과점유 방지

    except serial.SerialException as e:
        print(f"[!] 시리얼 통신 오류: {e}")
    except KeyboardInterrupt:
        print("\n[*] 사용자에 의해 수신이 중단되었습니다.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("[*] 포트가 안전하게 닫혔습니다.")




def serialDisconnectAll():
    global portlist, port_connected_checker, c6Label
    print("Disconnecting all serial ports...")

    for i in range(1, 10):
        # 1. 포트 객체가 존재하고 열려있는지 확인
        if portlist[i] is not None:
            try:
                if portlist[i].is_open:
                    portlist[i].close()  # 포트 닫기
                    print(f"COM{i} closed successfully.")
            except Exception as e:
                print(f"Error closing COM{i}: {e}")
            finally:
                # 2. 객체 초기화 (재사용 및 메모리 정리)
                portlist[i] = None

        # 3. UI 라벨 및 연결 플래그 업데이트
        if c6Label[i] is not None:
            c6Label[i].configure(text="DC", fg="black")
        if port_connected_checker[i] is not None:
            port_connected_checker[i] = "0"

    print("All ports disconnected.")




def serialCommend():
    #print (c7Entry[1].get())
    global portlist
    
    for i in range(1, 10):
        c7Entry[i]
    
    return



def serialTester():
    global portlist, c6Label, port_connected_checker
    
    if not is_running:
        return
    
    for i in range(1, 10):
        ser = portlist[i]

        if ser is not None and ser.is_open:
                try:
                    # 2. 버퍼에 쌓인 모든 줄을 빠르게 비우며 처리
                    while ser.in_waiting > 0:
                        # 줄바꿈 단위로 읽기 (포트 생성 시 timeout=0.02 이하 권장)
                        raw_line = ser.readline()
                        rx_text = raw_line.decode("utf-8", errors="ignore").strip()
        
                        if rx_text:
                            print(f"[RX] COM{i}: {rx_text}")
                            # GUI 라벨에 최신 수신값 반영
                            c6Label[i].configure(text=rx_text)
                            
                            # (선택) 하단 5줄 모니터링 라벨에도 로그 전달
                            # update_bottom_log(f"COM{i}: {rx_text}")
        
                except (serial.SerialException, OSError) as e:
                    print(f"COM{i} 통신 끊김/에러: {e}")
                    c6Label[i].configure(text="Error", fg="red")
                except Exception as e:
                    print(f"COM{i} 데이터 처리 에러: {e}")
    # 다음 폴링 예약 (50ms)
    #App.after(50, serialTester)
    
    return



def autoupdate():
    print ('enter auto update')
    return



def c7entrySender():
    #send MCU to entry data max len 8
    global portlist, c7Entry
    
    max_range = min(len(c7Entry), len(portlist))
    
    for i in range(1, max_range):
        entry_widget = c7Entry[i]
        
        if isinstance(entry_widget, tk.Entry):
            input_text_tmp = entry_widget.get().strip()
            
            if input_text_tmp:
                print(f"[DEBUG] 입력 감지 (COM{i}): {input_text_tmp}")
                ser = portlist[i]
                
                # 1. portlist[i] 객체 상태 확인
                if ser is not None:
                    print(f"[DEBUG] COM{i} 포트 객체 존재함. is_open = {ser.is_open}")
                    if ser.is_open:
                        try:
                            send_packet = (input_text_tmp + "\r\n").encode("utf-8")
                            ser.write(send_packet)
                            ser.flush()
                            print(f"[TX 성공] COM{i} -> {input_text_tmp}")
                            entry_widget.delete(0, tk.END)
                        except Exception as e:
                            print(f"[TX 에러] COM{i} 쓰기 실패: {e}")
                    else:
                        print(f"[확인 필요] COM{i} 객체는 있으나 포트가 닫혀(closed) 있습니다.")
                else:
                    print(f"[확인 필요] COM{i}에 연결된 포트 객체가 없습니다 (None). 'connect'를 먼저 눌렀는지 확인하세요.")
#    portlist[6].write(text.encode('utf-8'))
    return

def send_slot_command(slot_id, gcode):
    """지정된 슬롯 포트로 단일 G-code 전송"""
    global portlist
    if 1 <= slot_id < len(portlist):
        ser = portlist[slot_id]
        if ser is not None and ser.is_open:
            try:
                ser.write((gcode + "\r\n").encode("utf-8"))
                ser.flush()
                print(f"[TX Slot{slot_id}] {gcode}")
            except Exception as e:
                print(f"[!] Slot{slot_id} 전송 에러: {e}")
        else:
            print(f"[!] Slot{slot_id} 미연결 상태입니다.")


# ----------------------------------------------------
# 5. 4축 멀티라인 시퀀스 전송 엔진 (Tkinter Non-blocking)
# ----------------------------------------------------
class SequenceRunner:
    def __init__(self, slot_id=1, line_interval_ms=100, axis_interval_ms=1000):
        self.slot_id = slot_id
        self.line_interval_ms = line_interval_ms  # 같은 축 내 줄 간 전송 간격 (ms)
        self.axis_interval_ms = axis_interval_ms  # 축 변경 시 대기 간격 (ms)
        self.axis_queue = []
        self.current_axis_name = ""
        self.current_lines = []
        self.running = False

    def start(self):
        if self.running:
            print("[!] 이미 시퀀스가 동작 중입니다.")
            return

        ser = portlist[self.slot_id]
        if ser is None or not ser.is_open:
            print(f"[!] Slot {self.slot_id}이 연결되어 있지 않아 시퀀스를 시작할 수 없습니다.")
            return

        self.axis_queue = list(AXIS_GCODES.items())
        self.running = True
        print("\n=== 4축 멀티라인 G-code 시퀀스 시작 ===")
        self._next_axis()

    def _next_axis(self):
        if not self.running:
            return

        if not self.axis_queue:
            print("=== 모든 4축 루틴 전송 완료 ===\n")
            self.running = False
            return

        self.current_axis_name, self.current_lines = self.axis_queue.pop(0)
        self.current_lines = list(self.current_lines)  # 복사본
        print(f"\n--- [{self.current_axis_name}] 시작 (총 {len(self.current_lines)}줄) ---")
        self._send_next_line()

    def _send_next_line(self):
        if not self.running:
            return

        if self.current_lines:
            line = self.current_lines.pop(0).strip()
            if line and not line.startswith(";"):
                send_slot_command(self.slot_id, line)
            # 같은 축의 다음 줄 전송
            App.after(self.line_interval_ms, self._send_next_line)
        else:
            print(f"[{self.current_axis_name}] 완료. {self.axis_interval_ms/1000}초 대기...")
            # 다음 축으로 넘어가기 전 축 간격 딜레이 부여
            App.after(self.axis_interval_ms, self._next_axis)

    def stop(self):
        self.running = False
        print("[!] 4축 시퀀스 실행이 중단되었습니다.")

seq_runner = SequenceRunner(slot_id=1, line_interval_ms=100, axis_interval_ms=1500)

# ----------------------------------------------------
# 6. GUI 레이아웃 구성
# ----------------------------------------------------


App = tk.Tk()
App.title('myController')
App.resizable(width = False, height = False)
App.geometry('750x850+500+250')

App.rowconfigure(3, weight=1)
App.columnconfigure(0, weight=1)
App.columnconfigure(1, weight=1)
App.columnconfigure(2, weight=1)


#making menu
topmenu = tk.Menu(App)
filemenu = tk.Menu(topmenu, tearoff = 0)
#filemenu.add_command(label = 'connect', command = serialConnect)
filemenu.add_command(label = 'connect', command = autoDetectAndConnect)
filemenu.add_command(label = 'disconnect', command = serialDisconnectAll)
#filemenu.add_seperator()
filemenu.add_command(label = 'serialwrite_send', command = serialCommend)
filemenu.add_command(label = 'serialRead_buff', command = serialTester)

topmenu.add_cascade(label = 'portManager', menu = filemenu)

topmenu.add_cascade(label = 'ImageDetect', menu = filemenu)
App.config(menu = topmenu)

#making colum0label  

# LF1: Connection Info
myLF1 = tk.LabelFrame(App, text='connection', width=290, height=320, padx=2, pady=2, labelanchor='n')
myLF1.grid_propagate(False)
myLF1.grid(row=0, column=0, padx=15, pady=5)

for count, name in enumerate(portName):
    lbl = tk.Label(myLF1, text=name, padx=5, pady=5)
    lbl.grid(row=count, column=0)
    c0Label.append(lbl)

for count, stat in enumerate(initStat):
    lbl = tk.Label(myLF1, text=stat, padx=5, pady=5)
    lbl.grid(row=count, column=1)
    c1Label.append(lbl)

for count, buff in enumerate(initBuffer):
    lbl = tk.Label(myLF1, text=buff, padx=5, pady=5)
    lbl.grid(row=count, column=2)
    c2Label.append(lbl)

# LF2: Order Queue
myLF2 = tk.LabelFrame(App, text='orderQueue', width=150, height=320, padx=2, pady=2, labelanchor='n')
myLF2.grid_propagate(False)
myLF2.grid(row=0, column=1, padx=15, pady=5)

for count, name in enumerate(LF2body):
    lbl = tk.Label(myLF2, text=name, padx=5, pady=5)
    lbl.grid(row=count, column=0)
    c3Label.append(lbl)

for count, val in enumerate(LF2body_value):
    lbl = tk.Label(myLF2, text=val, padx=5, pady=5)
    lbl.grid(row=count, column=1)
    c4Label.append(lbl)

# LF3: Serial Status & Entry
myLF3 = tk.LabelFrame(App, text='Serial:COM(No.)', width=225, height=320, padx=2, pady=2, labelanchor='n')
myLF3.grid_propagate(False)
myLF3.grid(row=0, column=2, padx=15, pady=5)

for count, dev in enumerate(LF3cmos):
    lbl = tk.Label(myLF3, text=dev, padx=5, pady=5)
    lbl.grid(row=count, column=0)
    c5Label.append(lbl)

for count, stat in enumerate(LF3cmos_value):
    lbl = tk.Label(myLF3, text=stat, padx=5, pady=5)
    lbl.grid(row=count, column=1)
    c6Label.append(lbl)

for count, entry_name in enumerate(LF3cmos_entry):
    if count == 0:
        btn = tk.Button(myLF3, text='Send', width=7, command=c7entrySender)
        btn.grid(row=count, column=2, padx=2, pady=2)
        c7Entry.append(btn)
    else:
        ent = tk.Entry(myLF3, width=7)
        ent.grid(row=count, column=2)
        c7Entry.append(ent)

# Mid Frame: Control Buttons
mid_frame = tk.Frame(App, pady=10)
mid_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=10)

button_configs = [
    {"text": "4축 시퀀스 실행", "action": lambda: seq_runner.start()},
    {"text": "시퀀스 중단", "action": lambda: seq_runner.stop()},
    {"text": "닭 (G28)", "action": lambda: send_slot_command(1, "G28")},
    {"text": "목살 (G1)", "action": lambda: send_slot_command(1, "G1 X10 F1000")},
    {"text": "비상정지", "action": lambda: send_slot_command(1, "M112")}
]

for i, cfg in enumerate(button_configs):
    mid_frame.columnconfigure(i, weight=1)
    btn = tk.Button(mid_frame, text=cfg["text"], command=cfg["action"])
    btn.grid(row=0, column=i, padx=3, sticky="ew")

# Console Output Frame
console_frame = tk.LabelFrame(App, text='Standard Output Console', padx=5, pady=5)
console_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="nsew")

font_family = "Courier" if sys.platform == "darwin" else "Consolas"
console_text = tk.Text(
    console_frame,
    height=8,         # <- 표시할 줄 수 (기본 약 24줄 -> 8~12줄 추천)
    bg="#1e1e1e",
    fg="#d4d4d4",
    font=(font_family, 11),
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
    
    # 표준 출력 복구
    sys.stdout = orig_stdout
    sys.stderr = orig_stderr
    App.destroy()


# Tkinter 메인 루프 전에 프로토콜 등록


T1var = tk.IntVar()

##check box acrion #############################


#App.after(50, serialTester)
    

if __name__ == '__main__':
    #aa()
    #App.after(50, serialTester)
    App.protocol("WM_DELETE_WINDOW", on_closing)
    App.mainloop()
    print ('App close')
    #getCam()