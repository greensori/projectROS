조리 프로세스는 크게 총 5단계로 구성이 되는거고

아래 순서대로 일이 처리되는 것임

조리 프로세스
├── 1단계 pick and place
│   ├── unit1
│   │   |- motor_pwm.c      # 타이머 기반 PWM 출력 제어
│   │   |- motor_pwm.h
│   │   └- encoder.c        # 엔코더 펄스 카운트 입력
│   └── system_init.c       # 클럭 및 하드웨어 초기화
├── 2단계 unit change
│   ├── motor/
├── 2단계 unit change
│   ├── motor/
│   │   |- motor_pwm.c      # 타이머 기반 PWM 출력 제어
│   │   |- motor_pwm.h
│   │   └- encoder.c        # 엔코더 펄스 카운트 입력
│   └── comm/
│       |- uart.c           # 시리얼 통신 송수신
│       └- can.c            # CAN 통신 패킷 처리
│   │   └- encoder.c        # 엔코더 펄스 카운트 입력
│   └── comm/
│       |- uart.c           # 시리얼 통신 송수신
│       └- can.c            # CAN 통신 패킷 처리
├── 3단계 place and cook
│   ├── motor/
│   │   |- motor_pwm.c      # 타이머 기반 PWM 출력 제어
│   │   |- motor_pwm.h
│   │   └- encoder.c        # 엔코더 펄스 카운트 입력
│   └── comm/
│       |- uart.c           # 시리얼 통신 송수신
│       └- can.c            # CAN 통신 패킷 처리
├── 4단계 goto cook
│   ├── motor/
│   │   |- motor_pwm.c      # 타이머 기반 PWM 출력 제어
│   │   |- motor_pwm.h
│   │   └- encoder.c        # 엔코더 펄스 카운트 입력
│   └── comm/
│       |- uart.c           # 시리얼 통신 송수신
│       └- can.c            # CAN 통신 패킷 처리
└── 5단계 goto finish
    └── pin_config.h        # 핀 맵 및 파라미터 상수 정의
