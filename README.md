조리 프로세스는 크게 총 5단계로 구성이 되는거고

아래 순서대로 일이 처리되는 것이야

조리단계에서 각 메뉴들은 총 4개의 타이머를 가져야해

1. 총 조리시간을 기록하는 타이머(최대 12분, 하지만 초과할수 있음
2. 앞면의 총 조리시간을 기록하는 타이머(최대 6분, 하지만 초과할수 있음)
3. 뒷면의 총 조리시간을 기록하는 타이머(최대 6분, 하지만 초과할수 있음)
4. heat unit 조리시간을 기록하는 타이머(최대 2분, 하지만 초과할수 있음)

주문 단계에서 다음과 같이 3개의 변수를 새로 생성해야해
변수 1. (1-6)테이블 주문을 눌렀을때, 누적된 메뉴들의 수량과 테이블 번호를 기록 (테이블번호, 주문열(1-999), (주문 메뉴 목록))
   ├── 규칙1. 테이블 번호가 같아도, 주문버튼이 따로 눌러진 경우 메뉴는 각각 다르게 구분되서 조리되어야 함
   │   ├── 예시. 수블라키2개, 투움2개 테이블 1주문, 룰라2개, 투움2개 테이블 1주문인경우 각각 테이블 1: 주문열 1: 수블라키2, 투움2, 테이블1: 주문열 2: 룰라2, 투움2 형식으로 
변수 2. 조리가 완료되고, 6단계 finish stage에 진입한 경우 기록된 메뉴(변수1)를 접시에 담아야 하는데
  if (변수1의 수량 <= 3) 인 경우, 주문열이 동일한 경우
   ├── 6단계 1번 진행
   ├── 5단계 (변수 1의 수량만큼) 진행
   `- 조리완료 6-2단계 탈출 대기 트리거  (접시에 담긴 요리가 3개 미만이더라도 종결)
  if (변수 1의 수량 >= 4) 인 경우, 주문열이 동일한 경우
   ├── 6단계 1번 진행
   ├── 변수1 = 변수1 - 3
   ├── 변수1 수량이 0이 될떄까지 반복
   `- 완료
   if (변수1의 수량 <= 3) 인 경우, 주문열이 다른 경우
   ├── 6단계 1번 진행
   ├── 5단계 (변수 1의 수량만큼) 진행
   `- 완료 (접시에 담긴 요리가 3개 미만이더라도 종결)
변수 3. 잔여 접수 수량 stm_3(tim3 ch3),stm_3(tim3 ch4) 각각 20개
   



자동화 설비 요약 
이송유닛1. XYZ 이송 유닛 (Z축 말단에 PD2입력센서 존재, G40과 연동하여 물건 탐지시까지 이동 수행)
오픈유닛1. tim3
├── (stm_1)
│   ├── stm_unit_1. tim2 XYZ 이송 유닛 (Z축 말단에 PD2입력센서 존재, G40과 연동하여 물건 탐지시까지 이동 수행)
│   │   ├── (Z축 말단에 PD2입력센서 존재, G40과 연동하여 물건 탐지시까지 이동 수행)
│   │   ├── (X축 PC6입력센서 존재, G38과 연동하여 물건 탐지시까지 이동 수행)
│   │   ├── PC10(파지유닛 1), PC11(파지유닛2), PC12(예압조정)
│   ├── OPENER_1. tim3 ch1 (냉장고 1호 오픈)
│   ├── OPENER_2. tim3 ch2 (냉장고 2호 오픈)
│   ├── Ignite_starter_1. tim3 ch3. (별도 tkinter에 구동 버튼 작동, PC9 으로 안전밸브 해제)
│   ├── Ignite_starter_2. tim3 ch4. (별도 tkinter에 구동 버튼 작동, PC3 으로 안전밸브 해제)
│   ├── rodless_unit_1. (시작리미트 PC4, 엔드리미트 PC5)
│   │ 
├── (stm_2)
│   ├── stm_unit_2. tim2 XYZ 이송 유닛
│   │   ├── (테이블상단에 (stm1, PC7)입력센서 존재, G40과 연동하여 물건 탐지시까지 이동(도킹) 수행)
│   │   ├── (테이블상단에 (stm1, PC7)입력센서 존재, heat plated에서 요리 도킹시에 해당 센서 확인)
│   │   ├── (X축 PC6입력센서 존재, G38과 연동하여 물건 탐지시까지 이동 수행, heat plate에 전달하기 위함)
│   ├── PLATE_changer_1. tim3 ch1 (정방향리미트 PA9, 역방향리미트 PB9) (정방향 공압(PA4, 역방향 PC2)
│   ├── PLATE_changer_2. tim3 ch2 (정방향리미트 PA10, 역방향리미트 PC5) (정방향 공압(PB2, 역방향 PC3)
│   ├── Platter_1. tim3 ch3 () (소스 분배. 파슬리)
│   ├── Platter_2. tim3 ch4 () (소스 분배. 파프리카가루)
│   │ 
├── (stm_3)
│   ├── stm_unit_3. tim2 XYZ 이송 유닛. #컨베이어 이송완료된 접시를 받아야 함
│   │   ├── (테이블상단에 pd2입력센서 존재, G40과 연동하여 물건 탐지시까지 이동 수행)
│   │   ├── (X축 PC6입력센서 존재, G38과 연동하여 물건 탐지시까지 이동 수행)
│   ├── Finish_Conveyer_1. tim3 ch1 (리미트 PA9, 탐지프로브 PB9)   #장전된 접시 수량의 최대치 20개, 
│   ├── Finish_Conveyer_2. tim3 ch2 (리미트 PA10, 탐지프로브 PC5)   #장전된. 접시 수량의 최대치 20개, 1번 컨 
│   ├── DISH_Transfer_1. tim3 ch3 (접시장전유닛 1 하강)   #장전된 접시 수량의 최대치 20개, 홈복귀로 리미트 탐지까지 전진 
│   ├── DISH_Transfer_2. tim3 ch4 (접시장전유닛 2 하강).   #장전된 접시 수량의 최대치 20개, Tim3 ch3의 접시수량 소진시 tim3 ch4사용



조리 프로세스
├── 1단계 pick and place (stm_unit_1)
│   ├── EXEC_TRIGGER: 주문 대기열 존재 && 이전 공정 완료
│   ├── SENSOR_READ: M119 (타겟 핀: PD2, PC7, PC6)
│   │
│   ├── BRANCH_RULES:
│   │   ├── [RULE_A] IF (PD2: OPEN && 주문메뉴('수블라키', '투움')
│   │   │   └── ACTION_SEQUENCE:
│   │   │       |- M103 P0 S2000 F2000 D0   # 냉장고 오픈
│   │   │       `- G28                      # 시작전 복귀
│   │   │    
│   │   ├── [RULE_B] IF (PD2: OPEN && 주문메뉴('룰라', '비프샤슬릭', '치킨샤슬릭')
│   │   │   └── ACTION_SEQUENCE:
│   │   │       |- M103 P1 S2000 F2000 D0   # 냉장고 오픈
│   │   │       `- G28                      # 시작전 복귀
│   │   │
│   │   └── [RULE_C] IF (PD2: CLOSED)
│   │       └── ACTION_SEQUENCE:
│   │           `- G4 P1000                  # 1초 대기 후 M119 재조회
│   │  
│   ├── BRANCH_RULES:
│   │   ├── [CASE_A] IF (주문메뉴('수블라키')
│   │   │   └── ACTION_SEQUENCE:
│   │   │       `- G1 x2000                     # 축이동
│   │   ├── [CASE_B] IF (주문메뉴('투움')
│   │   │   └── ACTION_SEQUENCE:
│   │   │       `- G1 x2400                     # 축이동
│   │   ├── [CASE_C] IF (주문메뉴('룰라')
│   │   │   └── ACTION_SEQUENCE:
│   │   │       `- G1 x2800                     # 축이동
│   │   ├── [CASE_D] IF (주문메뉴('비프샤슬릭')
│   │   │   └── ACTION_SEQUENCE:
│   │   │       `- G1 x3300                     # 축이동
│   │   └── [CASE_E] IF (주문메뉴('치킨샤슬릭')
│   │       └── ACTION_SEQUENCE:
│   │           `- G1 x3600                     # 축이동
│   │ 
│   ├── COMMON_ACTIONS:
│   │   |- G38 X200 F200 (센서 탐지시(PC6)까지 이동)
│   │   |- G92 X0                # x축 재설정
│   │   |- G1 X-20 F1000         # x축 조정이동
│   │   |- G90                   # 절대 좌표 복귀
│   │   |- G1 z2000 
│   │   |- G1 y2000
│   │   |- G1 z200  
│   │   |- G40 (z축 센서 탐지시(PD2) 까지 이동, 냉장고 쪽)
│   │   |- M800 P4 S1 (공압유닛 작동)
│   │   |- M800 P5 S1 (공압유닛 작동)
│   │   `- G28 z y
│   │ 
│   └── BRANCH_RULES:
│       ├── [RULE_A] IF (PD2: OPEN && 주문메뉴('수블라키', '투움')
│       │   └── ACTION_SEQUENCE:
│       │       |- M128 P0   # 냉장고 닫기
│       │       `- M119                     # 머신 상태 조회
│       │    
│       └── [RULE_B] IF (PD2: OPEN && 주문메뉴('룰라', '비프샤슬릭', '치킨샤슬릭')
│          └── ACTION_SEQUENCE:
│               |- M128 P1   # 냉장고 닫기
│               `- M119                     # 머신 상태 조회
│
├── 2-1단계 unit change (stm_unit_2)
│   ├── EXEC_TRIGGER: 요리 조리타이머가 11분 30초를 초과한 상태가 없을 것 && 1단계 공정이 완료대기 상태일것
│   ├── SENSOR_READ: M119 (타겟 핀: PD2, PC7)
│   │
│   └── BRANCH_RULES:
│       ├── [RULE_A] IF (PC6: OPEN)
│       │   └── ACTION_SEQUENCE:
│       │       |- G1 X()                # stm보드_1 에서 x축의 좌표를 받아서 그 좌표 +2500만큼 거리를 이동
│       │       |- G38 X200 F200         # x축 센서탐지(PC6)까지 이동
│       │       |- G92 X0                # x축 재설정
│       │       |- G1 X-20 F1000         # x축 조정이동
│       │       `- G90                   # 절대 좌표 복귀
│       │    
│       └── [RULE_B] IF (PC6: CLOSED)
│           └── ACTION_SEQUENCE:
│               `- M119                  # 1초 대기 후 M119 재조회
│
├── 2-2단계 unit change (stm_unit_1)
│   └── COMMON_ACTIONS:
│       `- G40 (z축 센서(PC7) 탐지시 까지 이동, 이송유닛 쪽)
│
├── 2-3단계 unit change (stm_unit_2)
│   └── COMMON_ACTIONS:
│       |- M800 p0 S1
│       `- 1초 대기
│
├── 2-4단계 unit change (stm_unit_1)
│   ├── COMMON_ACTIONS:
│   │   |- M800 P0 S0
│   │   |- M800 P1 S0
│   │   |- 2초 대기
│   │   `- G28 
│   └── (이 단계 이후 조리대기 중인 요리가 있는 경우 1단계로 이동, 하지만 기존 코드는 순차적으로 계속 실행)
│
├── 3단계 cook and place (stm_unit_2) #2개의 heat unit이 있으며, 각각의heat unit에는 최대 7개의 메뉴가 들어갈수 있음
│   ├── EXEC_TRIGGER: 1 - 14번 heat unit중 idle 상태가 있을것, heat unit 1번 혹은 2번중 한개가 앞면을 표시하고 있을것
│   ├── SENSOR_READ: M119 (타겟 핀: PA9, PA10, PB9, PC5)
│   │
│   └── COMMON_ACTIONS:
│       |- G1 X()           # heat unit 자리 : 1번(x200), 2번(x400), .... 14번(x2800)
│       |- G1 Z1500 Y1500
│       |- M800 p0 s0
│       |- 1초 대기
│       |- M800 p2 s1
│       `- G28 Z Y
│
├── 4단계 go to cook (stm_unit_2) 
│   ├── EXEC_TRIGGER: NORMAL
│   ├── SENSOR_READ: M119 (타겟 핀: PA9, PA10, PB9, PC5)
│   │
│   └── BRANCH_RULES:
│       ├── [CASE_A] IF (PC6: OPEN)
│       │   └── ACTION_SEQUENCE:
│       │       |- M800 p7 s1
│       │       |- M103 p0 s2000 f2000 D0. #heat_unit1(stm_unit2_tim3_ch1) 위상변화 코드(앞->뒤) 
│       │       |- M103 p1 s2000 f2000 D1. #heat_unit2(stm_unit2_tim3_ch2) 위상변화 코드(뒤->앞) 
│       │       |- M800 p5 s0
│       │       |- M119
│       │       `- 2분 대기
│       │    
│       └── [CASE_B] IF (PC6: CLOSED)
│           └── ACTION_SEQUENCE:
│               |- M800 p5 s1
│               |- M103 p0 s2000 f2000 D1. #heat_unit1(stm_unit2_tim3_ch1) 위상변화 코드(뒤->앞) 
│               |- M103 p1 s2000 f2000 D0. #heat_unit2(stm_unit2_tim3_ch2) 위상변화 코드(앞->뒤) 
│               |- M800 p7 s0
│               |- M119
│               `- 2분 대기
│
├── 5단계 cook and place (stm_unit_2) 
│   ├── EXEC_TRIGGER: 총조리시간이 11분 50초을 초과한 요리가 있는 경우 그 위치로 이동 && pc6센서가 idle상태일것 
│   ├── SENSOR_READ: M119 (타겟 핀: (stm_1)PC7, (stm_2)PA9, (stm_2)PA10, (stm_2)PB9, (stm_2)PC5)
│   │
│   └── COMMON_ACTIONS:
│       |- G1 X()           # heat unit 자리 : 1번(x200), 2번(x400), .... 14번(x2800)
│       |- G28 Y
│       |- G28 Z
│       |- M800 P0 S1
│       |- G1 Y1500 Z1500
│       |- G28 X
│       `- M800 P0 S0     #공압해제 완료 (완료요리 카운터가 1개 올라감)
│
└── 6-1단계 finish stage (stm_unit_3) 
    ├── EXEC_TRIGGER: 총조리시간이 11분 초과한 요리가 있는 경우
    ├── SENSOR_READ: M119 (타겟 핀: PD2, PC7, PC6)
│   │
│   ├── BRANCH_RULES:
│       ├── [CASE_A] IF (tim3 ch3에 배정된 접시 잔여 수량이 1개 이상인 경우)
│       │   └── ACTION_SEQUENCE:
│       │       |- G39 P0 S20000 F400         #접시서빙 유닛 하강
│       │       |- M103 p3 s2000 f2000 D1.    #접시를 받아서 컨베이어 작동
│       │       `- G1 Z2000.   #z축 조정상승
│       │    
│       └── [CASE_B] IF (tim3 ch3에 배정된 접시 잔여 수량이 0개 인 경우)
│           └── ACTION_SEQUENCE:
│       │       |- G39 P1 S20000 F400         #접시서빙 유닛 하강, 센서 탐지 전진
│       │       |- M103 p3 s2000 f2000 D1.    #접시를 받아서 컨베이어 작동
│               `- G1 Z2000.   #z축 조정상승
│
└── 6-2단계 finish stage (stm_unit_3) 
    ├── EXEC_TRIGGER: 6-1단계 완료 및 완료대기 유닛이 없을것
    ├── SENSOR_READ: M119 (타겟 핀: PD2, PC7, PC6), 정기적으로 작동
│   │
│   ├── BRANCH_RULES:
│       ├── [CASE_A] IF (tim3 ch3에 배정된 접시 잔여 수량이 1개 이상인 경우)
│       │   └── ACTION_SEQUENCE:
│       │       |- G39 P0 S20000 F400         #접시서빙 유닛 하강
│       │       |- M103 p3 s2000 f2000 D1.    #접시를 받아서 컨베이어 작동
│       │       |- G1 Z200           # z축 조정 상승(컨베이어와 격리)
│       │       `- 파이썬에서 조리 완료 신호 대기.  #신호를 받아야 6-3단계로 이동
│       │    
│       └── [CASE_B] IF (tim3 ch3에 배정된 접시 잔여 수량이 0개 인 경우)
│           └── ACTION_SEQUENCE:
│               |- G39 P1 S20000 F400         #접시서빙 유닛 하강, 센서 탐지 전진
│               |- M103 p3 s2000 f2000 D1.    #접시를 받아서 컨베이어 작동
│       │       |- G1 Z200           # z축 조정 상승(컨베이어와 격리)
│       │       `- 파이썬에서 조리 완료 신호 대기.  #신호를 받아야 6-3단계로 이동
│
└── 6-3단계 finish stage (stm_unit_3) 
    ├── EXEC_TRIGGER: 파이썬에서 조리 완료 신호 수신
    ├── SENSOR_READ: M119 (타겟 핀: PD2, PC7, PC6), 정기적으로 작동
    │   
    └─── COMMON_ACTIONS: 
        |- G1 X2000            # x축 조정 상승(조리 내부공간에서 격리)
        |- G1 Y1500      # 2번 컨베이어로 조정 이동
        |- G1 Z0         # z축 조정 하강 (컨베이어2로 이동)
        `- M103 p3 s() f2000 D1.  # 컨베이어 이송(1테이블 1500, 2테이블 3000, 3테이블 4500)  


##############3



├── 1단계 pick and place (대상: stm_unit_1)
│   ├── EXEC_TRIGGER:
│   │   [조건] 주문 대기열 존재 && Unit 1 유휴 && stm1_pc7/pd2 안전 상태
│   │   [Python] any(item["status"] == "대기" for item in active_orders) and not is_unit1_busy and (sensor_states["stm1_pc7"] == "no trigger") and (sensor_states["stm1_pd2"] == "no trigger")
│   │
│   ├── SENSOR_READ:
│   │   [G-code] M119
│   │   [Target Pins] (stm_1) PD2, PC7, PC6
│   │
│   ├── BRANCH_RULES (냉장고 오픈 분기):
│   │   ├── [RULE_A] IF (PD2: OPEN && 주문메뉴 in ('수블라키', '투움'))
│   │   │   └── ACTION_SEQUENCE:
│   │   │       ├── M103 P0 S2000 F2000 D0    # 1호 냉장고 오픈 (tim3 ch1)
│   │   │       └── G28                       # 시작 전 축 복귀
│   │   │
│   │   ├── [RULE_B] IF (PD2: OPEN && 주문메뉴 in ('룰라', '비프샤슬릭', '치킨샤슬릭'))
│   │   │   └── ACTION_SEQUENCE:
│   │   │       ├── M103 P1 S2000 F2000 D0    # 2호 냉장고 오픈 (tim3 ch2)
│   │   │       └── G28                       # 시작 전 축 복귀
│   │   │
│   │   └── [RULE_C] IF (PD2: CLOSED)
│   │       └── ACTION_SEQUENCE:
│   │           └── G4 P1000                  # 1초 대기 후 M119 재조회 루프
│   │
│   ├── AXIS_TARGET_RULES (메뉴별 X축 초기 진입):
│   │   ├── [CASE_A] IF (메뉴 == '수블라키')     -> G1 X2000
│   │   ├── [CASE_B] IF (메뉴 == '투움')         -> G1 X2400
│   │   ├── [CASE_C] IF (메뉴 == '룰라')         -> G1 X2800
│   │   ├── [CASE_D] IF (메뉴 == '비프샤슬릭')   -> G1 X3300
│   │   └── [CASE_E] IF (메뉴 == '치킨샤슬릭')   -> G1 X3600
│   │
│   ├── COMMON_ACTIONS (파지 및 인출 공정):
│   │   ├── G38 X200 F200                     # PC6 센서 탐지 시까지 X축 전진
│   │   ├── G92 X0                            # X축 영점 재설정
│   │   ├── G1 X-20 F1000                     # X축 보정 후퇴
│   │   ├── G90                               # 절대 좌표계 복귀
│   │   ├── G1 Z2000                          # Z축 하강 진입
│   │   ├── G1 Y2000                          # Y축 슬롯 접근
│   │   ├── G1 Z200                           # Z축 안착
│   │   ├── G40                               # PD2 센서 탐지 시까지 Z축 이동
│   │   ├── M800 P4 S1                        # 그리퍼 공압 유닛 ON (PC10 파지 1)
│   │   ├── M800 P5 S1                        # 그리퍼 공압 유닛 ON (PC11 파지 2)
│   │   └── G28 Z Y                           # Z, Y축 안전 높이 복귀
│   │
│   └── BRANCH_RULES (냉장고 도어 클로즈):
│       ├── [RULE_A] IF (주문메뉴 in ('수블라키', '투움'))
│       │   └── ACTION_SEQUENCE:
│       │       ├── M128 P0                   # 1호 냉장고 닫기
│       │       └── M119
│       │
│       └── [RULE_B] IF (주문메뉴 in ('룰라', '비프샤슬릭', '치킨샤슬릭'))
│           └── ACTION_SEQUENCE:
│               ├── M128 P1                   # 2호 냉장고 닫기
│               └── M119
│
├── 2-1단계 unit change (대상: stm_unit_2 접근)
│   ├── EXEC_TRIGGER:
│   │   [조건] 1단계 완료대기 존재 && 11분 30초 초과 요리 부재 && Unit 2 유휴 && (stm1)PD2: triggered && (stm1)PC7: no trigger
│   │   [Python] any(item["status"] == "1단계:완료대기" for item in active_orders) and not has_cooking_over_limit() and not is_unit2_busy and (sensor_states["stm1_pd2"] == "triggered") and (sensor_states["stm1_pc7"] == "no trigger")
│   │
│   ├── SENSOR_READ:
│   │   [G-code] M119
│   │   [Target Pins] (stm_1) PD2, PC7 / (stm_2) PC6
│   │
│   └── BRANCH_RULES:
│       ├── [RULE_A] IF (stm2_pc6: OPEN)
│       │   └── ACTION_SEQUENCE:
│       │       ├── G1 X{b1_x + 2500}         # Unit 1 X좌표 기준 +2500 위치 접근
│       │       ├── G38 X200 F200             # PC6 센서 탐지 시까지 전진
│       │       ├── G92 X0                    # X축 영점 재설정
│       │       ├── G1 X-20 F1000             # X축 보정 이동
│       │       └── G90                       # 절대 좌표 복귀
│       │
│       └── [RULE_B] IF (stm2_pc6: CLOSED)
│           └── ACTION_SEQUENCE:
│               └── M119                      # 간섭 대기 후 재조회
│
├── 2-2단계 unit change (대상: stm_unit_1 도킹)
│   ├── EXEC_TRIGGER:
│   │   [조건] 2-1단계 stm_unit_2 접근 완료
│   │
│   └── COMMON_ACTIONS:
│       └── G40                               # (stm_1) PC7 도킹 센서 탐지 시까지 하강 이동
│
├── 2-3단계 unit change (대상: stm_unit_2 파지)
│   ├── EXEC_TRIGGER:
│   │   [조건] 2-2단계 도킹 완료 수신
│   │
│   └── COMMON_ACTIONS:
│       ├── M800 P0 S1                        # stm_unit_2 그리퍼 공압 파지 ON
│       └── G4 P1000                          # 1초 대기 (파지 안정화)
│
├── 2-4단계 unit change (대상: stm_unit_1 이탈 복귀)
│   ├── EXEC_TRIGGER:
│   │   [조건] 2-3단계 stm_unit_2 파지 완료
│   │
│   └── COMMON_ACTIONS:
│       ├── M800 P0 S0                        # stm_unit_1 그리퍼 공압 파지 OFF
│       ├── M800 P1 S0                        # stm_unit_1 보조 공압 OFF
│       ├── G4 P2000                          # 2초 압력 해제 대기
│       └── G28                               # stm_unit_1 원점 복귀 -> (stm_1) PC7 triggered 설정 -> 1단계 루프 재개 가능
│
├── 3단계 cook and place (대상: stm_unit_2)
│   ├── EXEC_TRIGGER:
│   │   [조건] 2단계 완료대기 존재 && 11분 30초 초과 요리 부재 && (stm1)PC7: triggered && 앞면 슬롯 잔여시간 >= 20초 확보
│   │   [Python] any(item["status"] == "2단계:완료대기" for item in active_orders) and not has_cooking_over_limit() and (sensor_states["stm1_pc7"] == "triggered") and (get_empty_heat_slot_in_front_plate() is not None) and not is_unit2_busy
│   │
│   ├── SENSOR_READ:
│   │   [G-code] M119
│   │   [Target Pins] (stm_2) PA9, PA10, PB9, PC5
│   │
│   └── COMMON_ACTIONS:
│       ├── G1 X{target_slot * 200}           # 대상 슬롯 좌표 이동 (1번: 200 ~ 14번: 2800)
│       ├── G1 Z1500 Y1500                    # 조리대 안착 좌표 진입
│       ├── M800 P0 S0                        # stm_unit_2 공압 해제 (요리 거치)
│       ├── G4 P1000                          # 1초 대기
│       ├── M800 P2 S1                        # 안착 고정 기구 작동
│       └── G28 Z Y                           # Z, Y축 복귀 -> 4대 타이머(총 조리, 앞면, 뒷면, 체류) 계측 개시
│
├── 4단계 go to cook (대상: stm_unit_2 / 플레이트 위상 회전)
│   ├── EXEC_TRIGGER:
│   │   [조건] 플레이트 위상 체류시간 2분 도달 && Unit 2 유휴 && 반전 락 해제 상태
│   │   [Python] (plate_phase_timer[1] >= 120.0 or plate_phase_timer[2] >= 120.0) and not is_unit2_busy and not (plate_flipping_lock[1] or plate_flipping_lock[2])
│   │
│   ├── SENSOR_READ:
│   │   [G-code] M119
│   │   [Target Pins] (stm_2) PC6, PA9, PA10, PB9, PC5
│   │
│   └── BRANCH_RULES:
│       ├── [CASE_A] IF (stm2_pc6: OPEN) -> 명령어 Set 1
│       │   └── ACTION_SEQUENCE:
│       │       ├── M800 P7 S1                # 공압 잠금 해제
│       │       ├── M103 P0 S2000 F2000 D0    # HP1 위상 반전 (앞 -> 뒤)
│       │       ├── M103 P1 S2000 F2000 D1    # HP2 위상 반전 (뒤 -> 앞)
│       │       ├── M800 P5 S0                # 고정 공압 체결
│       │       ├── M119                      # 리미트 상태 확인
│       │       └── [타이머 리셋]              # 해당 슬롯 heat_unit_stay_time = 0.0 초기화 후 2분 체류 주기 재개
│       │
│       └── [CASE_B] IF (stm2_pc6: CLOSED) -> 명령어 Set 2
│           └── ACTION_SEQUENCE:
│               ├── M800 P5 S1                # 공압 잠금 해제
│               ├── M103 P0 S2000 F2000 D1    # HP1 위상 반전 (뒤 -> 앞)
│               ├── M103 P1 S2000 F2000 D0    # HP2 위상 반전 (앞 -> 뒤)
│               ├── M800 P7 S0                # 고정 공압 체결
│               ├── M119                      # 리미트 상태 확인
│               └── [타이머 리셋]              # 해당 슬롯 heat_unit_stay_time = 0.0 초기화 후 2분 체류 주기 재개
│
├── 5단계 cook and place (대상: stm_unit_2 / 조리 완료 요리 추출)
│   ├── EXEC_TRIGGER:
│   │   [조건] 총 조리시간 11분 50초 초과 요리 존재 && 앞면 위치 && Unit 2 프리픽 위치 && stm2_pc6: idle
│   │   [Python] any(info["status"] in ["cooking", "finished"] and info["total_cook_time"] >= 710.0 and plate_current_side[info["plate_id"]] == "front" for info in heat_units.values()) and unit2_at_prepick_pos and (sensor_states["stm2_pc6"] == "no trigger") and not is_unit2_busy
│   │
│   ├── SENSOR_READ:
│   │   [G-code] M119
│   │   [Target Pins] (stm_1) PC7 / (stm_2) PC6, PA9, PA10, PB9, PC5
│   │
│   └── COMMON_ACTIONS:
│       ├── G1 X{target_slot * 200}           # 대상 조리대 위치 이동
│       ├── G28 Y                             # Y축 정렬
│       ├── G28 Z                             # Z축 취출 높이 진입
│       ├── M800 P0 S1                        # stm_unit_2 그리퍼 파지 ON
│       ├── G1 Y1500 Z1500                    # 조리대 공간에서 요리 인출 상승
│       ├── G28 X                             # X축 배출 존 이동
│       ├── M800 P0 S0                        # stm_unit_2 공압 해제 (접시/버퍼로 인계)
│       └── [내부 트리거]                      # [변수 2] 접시 담기 배칭 알고리즘으로 요리 전달 (단위: 1~3개)
│
├── 6-1단계 finish stage (대상: stm_unit_3 / 접시 사전 공급 및 컨베이어 기동)
│   ├── EXEC_TRIGGER:
│   │   [조건] 총 조리시간 11분(660초) 초과 요리 감지 && Unit 3 상태 IDLE
│   │   [Python] any(info["status"] == "cooking" and info["total_cook_time"] >= 660.0 for info in heat_units.values()) and unit3_stage6_status == "idle" and not is_unit3_busy
│   │
│   ├── SENSOR_READ:
│   │   [G-code] M119
│   │   [Target Pins] (stm_3) PD2, PC7, PC6, PA9, PA10, PB9, PC5
│   │
│   └── BRANCH_RULES ([변수 3] 잔여 접시 수량 판정):
│       ├── [CASE_A] IF (dish_stock['tim3_ch3'] >= 1)
│       │   └── ACTION_SEQUENCE:
│       │       ├── G39 P0 S20000 F400        # 1번 접시장전유닛(ch3) 하강 공급 (재고 -1)
│       │       ├── M103 P3 S2000 F2000 D1    # 수신 1번 컨베이어 가동
│       │       └── G1 Z2000                  # Z축 상승
│       │
│       └── [CASE_B] IF (dish_stock['tim3_ch3'] == 0 && dish_stock['tim3_ch4'] >= 1)
│           └── ACTION_SEQUENCE:
│               ├── G39 P1 S20000 F400        # 2번 접시장전유닛(ch4) 하강 공급 (재고 -1)
│               ├── M103 P3 S2000 F2000 D1    # 수신 1번 컨베이어 가동
│               └── G1 Z2000                  # Z축 상승
│
├── 6-2단계 finish stage (대상: stm_unit_3 / 접시 대기 및 요리 안착 격리)
│   ├── EXEC_TRIGGER:
│   │   [조건] 6-1단계 완료 && 접시 수령 완료 상태
│   │   [Python] unit3_stage6_status == "plate_fed" and not is_unit3_busy
│   │
│   ├── SENSOR_READ:
│   │   [G-code] M119
│   │   [Target Pins] (stm_3) PD2, PC7, PC6
│   │
│   └── COMMON_ACTIONS:
│       ├── G1 Z200                           # Z축 보정 상승 (컨베이어 공간 격리)
│       └── [신호 대기]                        # 파이썬 배칭 엔진으로부터 조리 완료 신호 수신 대기
│
└── 6-3단계 finish stage (대상: stm_unit_3 / 테이블별 최종 컨베이어 서빙)
    ├── EXEC_TRIGGER:
    │   [조건] 접시 적재 완료 트리거 수신:
    │          ① 동일 주문열(order_seq) 요리 3개 적재 완료
    │          ② 주문열 잔여 수량이 3개 미만이고 해당 주문열 조리가 모두 종료됨
    │          ③ 주문열이 다른 후속 요리가 도착하여 이전 접시 배출 필요
    │   [Python] (current_serving_plate["loaded_count"] >= 3 or same_seq_remaining == 0) and not is_unit3_busy
    │
    ├── SENSOR_READ:
    │   [G-code] M119
    │   [Target Pins] (stm_3) PD2, PC7, PC6
    │
    └── COMMON_ACTIONS:
        ├── G1 X2000                          # 내부 작업 공간 간섭 회피 이동
        ├── G1 Y1500                          # 2번 출구 컨베이어 정렬
        ├── G1 Z0                             # Z축 하강 도킹
        └── M103 P3 S{table_num * 1500} F2000 D1  # 테이블별 차등 거리 이송 (T1: 1500, T2: 3000, T3: 4500 ...)

처리 순서 정리(우선순위)
├── 1순위 : 4단계 goto cook
│   ├── stm보드_2 (heat unit 1에서 조리중인 상태의 2분을 초과한경우 전체가 위상변화, heat unit 2또한 같음) 
│   │   |- 규칙1. heat unit1 과 heat unit2는 서로 위치가 반대임
│   │   |- 규칙2. 매 2분 마다 앞면 뒷면이 변화함
│   │   └- 실행
│   └── 
├── 2순위 : 6단계 finish stage. #독립적으로 작동
│   ├── stm보드_3 
│   │   |- 규칙1. 접시 한개에 저장할 수 있는 완료된 요리의 최대 수량은 3개임
│   │   |- 규칙2. 1, 2, 3, 4, 5, 6테이블 주문별 요리는 각각 다른 접시에 처리 되어야 함
│   │   └- 실행
│   └── 
├── 3순위 : 1단계  #독립적으로 작동
│   ├── 조건1 : 주문완료되어 대기중인 요리가 있을 것
│   ├── 조건2 : stm보드 상 센서정보를 읽고, stm_unit_1(PC7, PD2) 센서가 no trigger 상태 
│   └── 실행
├── 4순위 : 5단계  # 조리 완료된 유닛은 빠르게 처리 되어야 함
│   ├── 조건1 : 타이머의 시간이 11분 30초을 초과한 요리가 있는경우(조리타이의 시간이 큰 것부터 우선적으로 처리)
│   └── 조건2 : stm보드 상 센서정보를 읽고, stm_unit_1(PC7) 센서가 no trigger 상태 
│   ├── 조건3 : 대상 heat unit의 상태가 앞면인 경우
│   ├── 조건4 : stm_unit_2가 픽업전 위치에 위치한 경우 
│   └── 실행
├── 5순위 : 2단계    #3단계 진행을 위한 선행 조건
│   ├── 조건1 : 요리 조리타이머가 11분 30초를 초과한 상태가 없을 것
│   ├── 조건2 : stm보드 상 센서정보를 읽고, stm_unit_1(PD2) 센서가 trigger 상태, stm_unit_1(PC7) 센서가 no trigger 상태 
│   ├── 조건3 : 1단계 공정이 완료대기 상태일것
│   └── 결과 : stm_unit_1(PC7)센서가 trigger 변화함
├── 6순위 : 3단계 
│   ├── 조건1 : 요리 조리타이머가 11분 30초를 초과한 상태가 없을 것
│   ├── 조건2 : stm_unit_1(PC7) 센서가 trigger 상태 
│   ├── 조건3 : 비어있는 조리대 칸이 앞면 상태일것
│   ├── 조건4 : 비어있는 조리대 칸이 상태 변화까지 남은 시간이 20초 이상일것
│   └── 실행
└── 




def schedule_pipeline():
    # [우선순위 1] 4단계: 2분 만료 위상 반전 (Set 1 또는 Set 2 실행)
    if not is_unit2_busy and (plate_phase_timer[1] >= 120.0 or plate_phase_timer[2] >= 120.0):
        rotate_both_plates_synchronized()
        return

    # [우선순위 2] 1단계: 주문 접수 재료 픽업 (Unit 1 독립 구동)
    if not is_unit1_busy and any(item["status"] == "대기" for item in active_orders):
        if sensor_states["stm1_pc7"] == "no trigger" and sensor_states["stm1_pd2"] == "no trigger":
            _start_stage1_pick(pending_item)

    if is_unit2_busy:
        return

    # [우선순위 3] 5단계: 11분 50초 초과 요리 배출 (앞면 플레이트 & PC6 IDLE)
    if finished_candidates and sensor_states["stm2_pc6"] == "no trigger" and unit2_at_prepick_pos:
        _run_stage5_finish(best_candidate_slot)
        return

    # [우선순위 4] 2단계: 11분 30초 초과 요리 없을 때 2-1 ~ 2-4 인계 진행
    if stage1_done_item and not has_cooking_over_limit():
        if sensor_states["stm1_pd2"] == "triggered" and sensor_states["stm1_pc7"] == "no trigger":
            _run_stage2_unit_change(stage1_done_item)
            return

    # [우선순위 5] 3단계: 앞면 빈 슬롯 & 위상 반전까지 잔여 시간 >= 20초 시 안착
    if stage2_done_item and not has_cooking_over_limit():
        if sensor_states["stm1_pc7"] == "triggered" and target_slot is not None:
            _run_stage3_cook_and_place(stage2_done_item, target_slot)
            return
