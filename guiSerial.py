   # -*- coding: utf-8 -*-


import time


import tkinter as tk
import serial
import serial.tools.list_ports
import threading
import queue



portName = ['portName', 'ttyS0 (UART0)', 'ttyTHS2 (UART1)', 'i2c (master)'
            , 'USB 3.0 (CMOS)', 'USB OTG', 'GPIO (H13)', 'GPIO (G14)'
            , 'GPIO (A22)', 'GPIO (A23)']
initStat = ['status', 'connect', 'connect', 'openDrain', 'connect'
            , 'notin', 'gpio_pq4_pi4', 'can_gpio2_paa2', 'gpio_mdm7_py6', 'gpio_mdm1_py0']
initBuffer = ['bufferSize', '0', '0', '0', '0', '0', '0', '0', '0', '0']

LF2body = ['menuName', '-', '-', '-', '-', '-'
           , '-', '-', '-', '-']

LF2body_value = ['now?', '0', '0', '0', '0', '0', '0', '0', '0', '0']



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

port_connected_checker = ['checker', '0', '0', '0', '0', '0', '0', '0', '0', '0']


portlist = ['portlist']
for i in range(1, 10):
    portlist.append('port%d' %i)



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
    
    return



def autoupdate():
    print ('enter auto update')
    return



def c7entrySender():
    #send MCU to entry data max len 8
    global portlist, c7Entry
    
    for i in range(1, 10):
        input_text_tmp = c7Entry[i].get().strip()
        if input_text_tmp:
            print (input_text_tmp)
            ser = portlist[i]
            if ser is not None and ser.is_open:
                try:
                    send_packet = (input_text_tmp + "\r\n").encode("utf-8")
                    ser.write(send_packet)
                    print(f"[TX] COM{i} -> {input_text_tmp} ({len(input_text_tmp)} bytes)")
                except Exception as e:
                    print(f"COM{i} 전송 에러: {e}")
            else:
                print(f"COM{i} 포트 미연결 (데이터: {input_text_tmp})")
#    portlist[6].write(text.encode('utf-8'))
    return






App = tk.Tk()
App.title('myController')
App.resizable(width = False, height = False)
App.geometry('750x850+500+250')

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

myLF1 = tk.LabelFrame(App, text = 'connection', width = 290, height =320, padx = 2, pady = 2, labelanchor = 'n')
myLF1.grid_propagate(False)
myLF1.grid(row = 0, column = 0, padx = 15, pady = 5)
#myLF1.place(x = 10, y = 10)
count = 0
for i in portName:
    #print (count)
    c0Label.append(int(count))
    c0Label[count]= tk.Label(myLF1, text = i, padx = 5, pady = 5)
    c0Label[count].grid(row = count, column = 0)
    count = count + 1
count = 0
for i in initStat:
    c1Label.append(int(count))
    c1Label[count] = tk.Label(myLF1, text = i, padx = 5, pady = 5)
    c1Label[count].grid(row = count, column = 1)
    count = count + 1
count = 0
for i in initBuffer:
    c2Label.append(i)
    c2Label[count] = tk.Label(myLF1, text = i, padx = 5, pady = 5)
    c2Label[count].grid(row = count, column = 2)
    count = count + 1

#making 2nd labelframe
myLF2 = tk.LabelFrame(App, text = 'orderQueue', width = 150, height =320, padx = 2, pady = 2, labelanchor = 'n')
myLF2.grid_propagate(False)
myLF2.grid(row = 0, column = 1, padx = 15, pady = 5)
count = 0
for i in LF2body:
    c3Label.append(i)
    c3Label[count] = tk.Label(myLF2, text = i, padx = 5, pady = 5)
    c3Label[count].grid(row = count, column = 0)
    count = count + 1

count = 0
for i in LF2body_value:
    c4Label.append(i)
    c4Label[count] = tk.Label(myLF2, text = i, padx = 5, pady = 5)
    c4Label[count].grid(row = count, column = 1)
    count = count + 1    

#making 3rd labelFrame
myLF3 = tk.LabelFrame(App, text = 'Serial:COM(No.)',width = 225, height =320, padx = 2, pady = 2, labelanchor = 'n')
myLF3.grid_propagate(False)
myLF3.grid(row = 0, column = 2, padx = 15, pady = 5)
count = 0
for i in LF3cmos:
    c5Label.append(i)
    c5Label[count] = tk.Label(myLF3, text = i, padx = 5, pady = 5)
    c5Label[count].grid(row = count, column = 0)
    count = count + 1  
    
count = 0
for i in LF3cmos_value:
    c6Label.append(i)
    c6Label[count] = tk.Label(myLF3, text = i, padx = 5, pady = 5)
    c6Label[count].grid(row = count, column = 1)
    count = count + 1    
    

def send_midbtn_command(mcu_id, gcode):
    print(f"[전송] MCU-{mcu_id} -> {gcode}")
    
    
menu_counts = {
        "닭" : 0,
        "목살" : 0,
        "떡갈" : 0,
        "제육" : 0,
        "야채" : 0
        }

menu_buttons = {}
    
    
button_configs = [
    {"text": "닭(  0  개)", "action": lambda: send_midbtn_command(1, "G28")},
    {"text": "목살( 0 개)", "action": lambda: send_midbtn_command(1, "G1 X10 F1000")},
    {"text": "떡갈( 0 개)", "action": lambda: send_midbtn_command(2, "M104 S200")},
    {"text": "제육( 0 개)", "action": lambda: send_midbtn_command(3, "M106 S255")},
    {"text": "야채( 0 개)", "action": lambda: send_midbtn_command(1, "M112")},
    {"text": "주 문 완 료", "action": lambda: send_midbtn_command(1, "M112")},
    {"text": "초  기  화", "action": lambda: send_midbtn_command(1, "M112")}
]
    
mid_frame = tk.Frame(App, pady = 10)
mid_frame.grid(row = 1, column = 0, columnspan = 3, sticky="ew", padx = 5, pady  = 10)

buttons = []
for i, cfg in enumerate(button_configs):
    mid_frame.columnconfigure(i, weight=1)
    btn = tk.Button(
        mid_frame,
        text=cfg["text"],
        command=cfg["action"]  # 딕셔너리에 정의된 동작 연결
    )
    btn.grid(row=0, column=i, padx=3, sticky="ew")
    buttons.append(btn)






count = 0 #0 for label

label_tmp = tk.Label(App, text = 'device(com)_connect port()', fg = 'blue', font=('arial', 15))
label_tmp.grid(row = 2, column = 0, padx = 15, pady = 5, stick = 'w')

label_tmp2 = tk.Label(App, text = 'device(com)_connect port()', fg = 'blue', font=('arial', 15))
label_tmp2.grid(row = 3, column = 0, padx = 15, pady = 5, stick = 'w')

label_tmp3 = tk.Label(App, text = 'device(com)_connect port()', fg = 'blue', font=('arial', 15))
label_tmp3.grid(row = 4, column = 0, padx = 15, pady = 5, stick = 'w')

label_tmp3 = tk.Label(App, text = 'idevice(com)_connect port()', fg = 'blue', font=('arial', 15))
label_tmp3.grid(row = 5, column = 0, padx = 15, pady = 5, stick = 'w')

label_tmp3 = tk.Label(App, text = 'order __ in', fg = 'blue', font=('arial', 15))
label_tmp3.grid(row = 6, column = 0, padx = 15, pady = 5, stick = 'w')

label_tmp3 = tk.Label(App, text = 'order __ in', fg = 'blue', font=('arial', 15))
label_tmp3.grid(row = 7, column = 0, padx = 15, pady = 5, stick = 'w')




def update_bottom_log(text):
    """하단 5개 라벨을 FIFO 방식으로 한 칸씩 올리며 새 로그 출력"""
    global bottom_labels
    if not bottom_labels:
        return
    # 0번부터 3번 라벨의 텍스트를 다음 라벨로 복사 (밀어올리기)
    for i in range(len(bottom_labels) - 1):
        bottom_labels[i].configure(text=bottom_labels[i+1].cget("text"))
    # 맨 마지막 라벨에 새 메시지 반영
    bottom_labels[-1].configure(text=text)




#c7Entry.append(1)
#c7Entry[0] = tk.Label(myLF3, text = LF3cmos_entry[0], padx = 5, pady = 5)
for i in LF3cmos_entry:
    if (count == 0):
        c7Entry.append(i)
        c7Entry[count] = tk.Button(myLF3, text = 'Send', width = 7, command = c7entrySender)
        c7Entry[count].grid(row = count, column = 2, padx = 2, pady = 2)
        #c7Entry[count] = tk.Label(myLF3, text = i, padx = 5, pady = 5)
        #c7Entry[count].grid(row=count, column=2)
        count = count + 1
    else:
        c7Entry.append(i)
        c7Entry[count] = tk.Entry(myLF3, width = 7)
        c7Entry[count].grid(row = count, column = 2)
        count = count + 1    
        
        

def on_closing():
    # 창 닫힐 때 모든 포트 먼저 닫기
    serialDisconnectAll()
    App.destroy()


# Tkinter 메인 루프 전에 프로토콜 등록


T1var = tk.IntVar()

##check box acrion #############################


App.after(50, serialTester)
    

if __name__ == '__main__':
    #aa()
    App.after(50, serialTester)
    App.protocol("WM_DELETE_WINDOW", on_closing)
    App.mainloop()
    print ('App close')
    #getCam()