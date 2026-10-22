조리 프로세스는 크게 총 5단계로 구성이 되는거고

아래 순서대로 일이 처리되는 것이야

[전체 공정 흐름도]
[대기열 주문] ──> [1단계: stm1 피킹] ──> [로드리스 이송]
                                              │
[3단계: 앞면 안착] <── [2단계: stm1->stm2 인계] <┘
        │
        ├──> [4단계: 2분 주기 교번 위상 반전 (Set1/Set2)]
        │
[11분 도달] ──> [6-1, 6-2단계: stm3 접시 사전 급송 및 Z200 대기]
        │
[11분 50초 도달] ──> [5단계: stm2 조리 완료 배출]
                            │
                            └──> [6단계 접시 적재 (최대 3개 배칭)] ──> [6-3단계: 테이블별 컨베이어 최종 서빙]


                            

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
│   │   ├── PC10(파지유닛), PC11(예압조정)
│   ├── OPENER_1. tim3 ch1 (냉장고 1호 오픈)
│   ├── OPENER_2. tim3 ch2 (냉장고 2호 오픈)
│   ├── Platter_1. tim3 ch3 () (소스 분배. 파슬리)
│   ├── Platter_2. tim3 ch4 () (소스 분배. 파프리카가루)
│   ├── rodless_unit_1. (시작 PC2, 엔드pc3) (시작리미트 pd2, 엔드리미트 pb7), (pc12 도킹 파지, 확인 센서 pb5). #미지정 인풋 유닛
│   │ 
├── (stm_2)
│   ├── stm_unit_2. tim2 XYZ 이송 유닛
│   │   ├── (테이블상단에 (PB9)입력센서 존재, G39과 연동하여 물건 탐지시까지 이동(도킹) 수행, 도킹 그리퍼 pc12)
│   │   ├── (X축 PC9입력센서 존재, G38과 연동하여 물건 탐지시까지 이동 수행, heat plate에 전달하기 위함)
│   ├── PLATE_changer_1. tim3 ch1 (정방향리미트 PB13, 역방향리미트 PC8) (정방향 공압 & 락링(PC2)
│   ├── PLATE_changer_2. tim3 ch2 (정방향리미트 PB14, 역방향리미트 PC6) (정방향 공압 & 락킹(PC3)
│   ├── Ignite_starter_1. tim3 ch3. (별도 tkinter에 구동 버튼 작동, PC10 으로 안전밸브 해제)
│   ├── Ignite_starter_2. tim3 ch4. (별도 tkinter에 구동 버튼 작동, PC11 으로 안전밸브 해제)
│   │ 
├── (stm_3)
│   ├── stm_unit_3. tim2 XYZ 이송 유닛. #컨베이어 이송완료된 접시를 받아야 함
│   │   ├── (테이블상단에 PB9입력센서 존재, M119과 연동하여 물건 탐지시 이동 수행)
│   │   ├── (X축 PC6입력센서 존재, G38과 연동하여 물건 탐지시까지 이동 수행)
│   │   ├── 도킹유닛 3에서 아이템을 받아서 고정 후 드랍하는 유닛(PC12) 
│   ├── Finish_Conveyer_1. tim3 ch1 (리미트 PB13, 탐지프로브 PC8)   #장전된 접시 수량의 최대치 20개, tim2 유닛 바로 위에 상단에 있음
│   ├── Finish_Conveyer_2. tim3 ch2 (리미트 PB14, 탐지프로브 PC6)   #장전된. 접시 수량의 최대치 20개, tim3와 연동하여 tim2 유닛까지 이송
│   ├── DISH_Transfer_1. tim3 ch3 (접시장전유닛 1 하강)   #장전된 접시 수량의 최대치 20개, 홈복귀로 리미트 탐지까지 전진 
│   ├── DISH_Transfer_2. tim3 ch4 (접시장전유닛 2 하강).   # tim2에서 접시를 받아서 이송... 



조리 프로세스
├── 1단계 pick and place (stm_unit_1)
│   ├── EXEC_TRIGGER: 주문 대기열 존재 && 1-1단계 공정상태('idle')상태
│   ├── SENSOR_READ: M119 (타겟 핀: PB9, PD2, PB7, tim2 좌표 동기화)
│   ├── COMMON_ACTIONS: 1-1단계 공정상태('busy') 변경
│   │
│   ├── BRANCH_RULES:
│   │   ├── [RULE_A] IF (PB9: OPEN && 주문메뉴('수블라키', '투움')
│   │   │   └── ACTION_SEQUENCE:
│   │   │       |- M103 P0 S2000 F2000 D0   # 냉장고 오픈
│   │   │       `- G28                      # 시작전 복귀
│   │   │    
│   │   ├── [RULE_B] IF (PB9: OPEN && 주문메뉴('룰라', '비프샤슬릭', '치킨샤슬릭')
│   │   │   └── ACTION_SEQUENCE:
│   │   │       |- M103 P1 S2000 F2000 D0   # 냉장고 오픈
│   │   │       `- G28                      # 시작전 복귀
│   │   │
│   │   └── [RULE_C] IF (PB9: CLOSED)
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
│   │   |- G1 z2000              # 충돌방지를 위한 위치 셋업
│   │   |- G1 y2000              # 회전
│   │   |- G1 z200               # 하강
│   │   |- G40 (z축 센서 탐지시(PD2) 까지 이동, 냉장고 쪽)
│   │   |- M800 P2 S1 (공압유닛(그립) 작동)
│   │   |- M800 P3 S1 (공압유닛(조정예압) 작동)
│   │   |- G28 z y    (상승 후 회전 홈 복귀)
│   │   |- G28 x    (최종 도킹 전 위치 정렬 완료)
│   │   `- 1-1단계 공정상태('complete') 변경
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
│   │ 
│   └── BRANCH_RULES:
│       ├── [RULE_A] IF (PB9: CLOSE and PD2: CLOSE) AND 1-1단계 공정상태('complete') AND 1-2단계 공정상태('idle')  #로드리스 도킹 준비
│       │   └── ACTION_SEQUENCE:
│       │       |- 1-2단계 공정상태('busy') 변경
│       │       |- G1 Z200                     # tim2 유닛 하강
│       │       |- M800 P4 S1                  # 도킹 공압유닛 작동
│       │       |- M800 P2 S0                  # tim2 공압유닛 해제
│       │       |- M800 P3 S0                  # tim2 공압유닛 해제
│       │       |- 1초 대기
│       │       |- G1 Z1500                    # 로드리스 충동 방지 위한 상승
│       │       |- M800 P1 S1                  # 로드리스 공압유닛 작동(엔드축으로)
│       │       |- M800 P0 S0                  # 로드리스 공압유닛 작동(엔드축으로)
│       │       `- 1-1단계 공정상태('idle') 변경.   # tim2 유닛 전달 완료
│       │    
│       └── [RULE_B] IF (PB9: CLOSE && PD2: OPEN) OR 1-1단계 공정상태('complete')
│          └── ACTION_SEQUENCE:
│               |- 1초 대기
│               `- M119                     # 머신 상태 조회
│       │    
│       └── [RULE_C] IF (PB9: OPEN) AND 1-1단계 공정상태('complete')
│          └── ACTION_SEQUENCE:
│               `- 시스템 메세지 전송 -> 그립유닛 누락, 장비 확인 필요. (apex5 -> 컨트롤러로 jog 기능 활용, 전 대기열 메뉴 초기화 이후 1-1단계 재진입 및 tim2유닛 위치 조정, 이동중 출동 주의)
│ 
│   │ 
│   └── BRANCH_RULES:  #(도킹유닛 3 전달 위치로 이동 완료 과정)
│       ├── [RULE_A] IF (PB7: CLOSE && 1-2단계 공정상태('busy')
│       │   └── ACTION_SEQUENCE:
│       │       |- 1초 대기                   # 로드리스가 현재 작동중
│       │       `- M119                     # 머신 상태 조회
│       │    
│       └── [RULE_B] IF (PB7: OPEN && 1-2단계 공정상태('busy')
│          └── ACTION_SEQUENCE:
│               |- M800 P0 S0    # 로드리스 공압 해제
│               |- M800 P1 S0.   # 로드리스 공압 해제
│               `- 1-2단계 공정상태('complete') 변경
│
├── 2-1단계 unit change (stm_unit_2)
│   ├── EXEC_TRIGGER: 요리 조리타이머가 11분 30초를 초과한 상태가 없을 것 && 1-2단계 공정상태('complete') && 2-1단계 공정상태('idle') && PB9(OPEN)
│   ├── SENSOR_READ: M119 (타겟 핀: PB9, tim2 위치 동기화)
│   ├── COMMON_ACTIONS: 2-1단계 공정상태('busy') 변경
│       |- G28 Y Z            # 도킹유닛2과 충돌을 피하기 위해서 홈 복귀 
│       |- G1 X2500           # 도킹유닛2 x축 정렬
│       |- G37 X200           # 도킹유닛2 x축 정렬(센서 탐지 이동)
│       |- G1 Y200 Z1500      # 도킹유닛2 YZ축 정렬( ) 
│       |- G37 Z200.          # 도킹유닛2 그랩 전 Z축 정렬( )
│       |- M800 P4 S1.        # 도킹유닛3 아이템 그립
│       `- 2-1단계 공정상태('complete') 변경
│
├── 2-2단계 unit change (stm_unit_1)
│   ├── EXEC_TRIGGER: 2-2단계 공정상태('idle') && 2-1단계 공정상태('complete')
│   ├── SENSOR_READ: M119 (타겟 핀: PB9, PB5, PD2)
│   └── COMMON_ACTIONS:
│       |- M800 P4 S0                     # 도킹유닛2 파지 해제 
│       `- 2-2단계 공정상태('busy') 변경       # 
│
├── 2-3단계 unit change (stm_unit_2)
│   ├── EXEC_TRIGGER: 2-2단계 공정상태('busy') && 2-1단계 공정상태('complete') && 1-2단계 공정상태('complete')
│   ├── SENSOR_READ: M119 (타겟 핀: PB9, PB5, PD2)
│   └── COMMON_ACTIONS:
│       |- G1 Y500           # 도킹유닛2 x축 이동 (도킹유닛 2와 충돌을 피하기 위함)
│       |- 1초 대기
│       `- 2-2단계 공정상태('complete') 변경
│
├── 2-4단계 unit change (stm_unit_1)
│   ├── EXEC_TRIGGER: 2-2단계 공정상태('complete') && 2-1단계 공정상태('complete') && 1-2단계 공정상태('complete') && 2-4단계 공정상태('idle')
│   ├── SENSOR_READ: M119 (타겟 핀: PB9, PB5, PD2)
│   ├── COMMON_ACTIONS:
│   │   |- 2-4단계 공정상태('busy') 변경
│   │   |- M800 P0 S0.  # 도킹유닛2 시작지점으로 이동
│   │   |- M800 P1 S1.  # 도킹유닛2 시작지점으로 이동
│   │   |- 2초 대기
│   │   `- 2-2단계 공정상태('idle'), 1-2단계 공정상태('idle'), 2-4단계 공정상태('complete') 변경.  #센서가 트리거 되어야 함
│   └── (이 단계 이후 조리대기 중인 요리가 있는 경우 1단계로 이동, 하지만 기존 코드는 순차적으로 계속 실행)
│
├── 3단계 cook and place (stm_unit_2) #2개의 heat unit이 있으며, 각각의heat unit에는 최대 7개의 메뉴가 들어갈수 있음
│   ├── EXEC_TRIGGER: 1 - 14번 heat unit중 idle 상태가 있을것, heat unit 1번 혹은 2번중 한개가 앞면을 표시하고 있을것, 2-4단계 공정상태('complete'), 3-1단계 공정상태('idle')
│   ├── SENSOR_READ: M119 (타겟 핀: PA9, PA10, PB9, PC5)
│   │
│   └── COMMON_ACTIONS:
│       |- 3-1단계 공정상태('busy') 변경 
│       |- G1 X()           # heat unit 자리 : 1번(x200), 2번(x400), .... 14번(x2800)
│       |- G1 Z1500 Y1500.  
│       |- M800 p0 s0
│       |- 1초 대기
│       |- M800 p2 s1.       # 공압 유닛 락킹
│       |- G28 Y Z.          # 정위치로
│       `- 2-1단계 공정상태('idle'), 2-4단계 공정상태('idle'), 3-1단계 공정상태('idle')  변경
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
├── 5-1단계 cook and place (stm_unit_2) 
│   ├── EXEC_TRIGGER: 총조리시간이 11분 30초을 초과한 요리가 있는 경우 그 위치로 이동 && pc6센서가 idle상태일것 && 5-1단계 공정상태('idle') && 2-1단계 공정상태('idle')
│   ├── SENSOR_READ: M119 (타겟 핀: (stm_1)PC7, (stm_2)PA9, (stm_2)PA10, (stm_2)PB9, (stm_2)PC5)
│   │
│   └── COMMON_ACTIONS:
│       |- 5-1단계 공정상태('busy') 변경
│       |- G1 X()           # heat unit 자리 c: 1번(x200), 2번(x400), .... 14번(x2800)
│       |- G28 Y
│       |- G28 Z
│       |- M800 P0 S1
│       |- G1 Y1500 Z1500
│       |- G28 X
│       |- M800 P0 S0     #공압해제 완료 (완료요리 카운터가 1개 올라감)
│       `- 5-1단계 공정상태('complete') 변경
│
├── 5-2단계 cook and place (stm_unit_3) 
│   ├── EXEC_TRIGGER: 5-1단계 공정상태('complete') && 5-2단계 공정상태('idle') && 2-1단계 공정상태('idle')
│   ├── SENSOR_READ: M119 (타겟 핀: (stm_1)PC7, (stm_2)PA9, (stm_2)PA10, (stm_2)PB9, (stm_2)PC5)
│   │
│   └── COMMON_ACTIONS:
│       |- 5-2단계 공정상태('busy') 변경
│       |- M800 P0 S1.    # 공압유닛 그리퍼 작동 
│       `- 5-2단계 공정상태('complete') 변경
│ 
├── 5-3단계 cook and place (stm_unit_2) 
│   ├── EXEC_TRIGGER: 5-1단계 공정상태('complete') && 5-2단계 공정상태('complete') && 2-1단계 공정상태('idle')
│   ├── SENSOR_READ: M119 (타겟 핀: (stm_1)PC7, (stm_2)PA9, (stm_2)PA10, (stm_2)PB9, (stm_2)PC5)
│   │
│   └── COMMON_ACTIONS:
│       |- M800 P0 S0     #공압해제 완료 (완료요리 카운터가 1개 올라감)
        |- G28 Y.       #충돌방지 해제
│       `- 5-1단계 공정상태('idle'), 5-2단계 공정상태('idle'), 완료요리카운터 +1 변경
│ 
│
└── 6-1단계 finish stage (stm_unit_3) 
    ├── EXEC_TRIGGER: 6-1단계 공정상태('idle') AND PB9 : OPEN
    ├── SENSOR_READ: M119 (타겟 핀: PD2, PC7, PC6)
    │   ├── COMMON_ACTIONS:
│   │   |- 6-1단계 공정상태('busy') 변경
│   │
│   ├── BRANCH_RULES:
│       ├── [CASE_A] IF (tim3 ch1에 배정된 접시 잔여 수량이 1개 이상인 경우)
│       │   └── ACTION_SEQUENCE:
│       │       |- G39 P0 S20000 F400         #접시서빙 유닛 하강
│       │       |- G1 Z2000.   #z축 조정상승
│       │       `- 6-1단계 공정상태('complete') 변경
│       │    
│       └── [CASE_B] IF (tim3 ch1에 배정된 접시 잔여 수량이 0개 인 경우)
│           └── ACTION_SEQUENCE:
│       │       |- G39 P1 S20000 F400         #접시서빙 유닛 하강, 센서 탐지 전진
│       │       |- M103 p3 s2000 f2000 D1.    #접시를 받아서 컨베이어 작동
│       │       |- G1 Z2000.   #z축 조정상승
│       │       `- 6-1단계 공정상태('complete') 변경
│
│
└── 6-2단계 finish stage (stm_unit_3) 
    ├── EXEC_TRIGGER: 6-1단계 공정상태('complete') AND 완료요리 카운터 > 0
    ├── SENSOR_READ: M119 (타겟 핀: PD2, PC7, PC6), 정기적으로 작동
    │   
    └─── COMMON_ACTIONS: 
        |- M800 P1 S1            # x축 조정 이동 (조리 내부공간에서 격리)
        |- G1 X2000            # x축 조정 이동 (조리 내부공간에서 격리)
        |- G1 Y1500      # 2번 컨베이어로 조정 이동
        |- G1 Z0         # z축 조정 하강 (컨베이어2로 이동)
        |- M103 p3 s() f2000 D1.  # 컨베이어 이송(1테이블 1500, 2테이블 3000, 3테이블 4500)  
        `- 누적적재량 = 0, 완료요리 카운터 = 0


##############3

├── 1단계 pick and place (대상: stm_unit_1)
│   ├── EXEC_TRIGGER:
│   │   [조건] 주문 대기열 존재 && Unit 1 유휴 && stm1_pc7/pd2 안전 상태
│   │   [Python] any(item["status"] == "대기" for item in active_orders) and not is_unit1_busy and (sensor_states["stm1_pc7"] == "no trigger") and (sensor_states["stm1_pd2"] == "no trigger")
│   │
│   ├── SENSOR_READ:
│   │   [G-code] M119
│   │   [Target Pins] (stm_1) PD2, PC6, PC7, PB9
│   │
│   ├── COMMON_ACTIONS (시작):
│   │   [Python] is_unit1_busy = True; target_item["status"] = "1단계:Pick"
│   │
│   ├── BRANCH_RULES (냉장고 도어 오픈):
│   │   ├── [RULE_A] IF target_item["name"] in ["수블라키", "투움"]
│   │   │   └── ACTION_SEQUENCE: M103 P0 S2000 F2000 D0 -> G28
│   │   └── [RULE_B] IF target_item["name"] in ["룰라", "비프샤슬릭", "치킨샤슬릭"]
│   │       └── ACTION_SEQUENCE: M103 P1 S2000 F2000 D0 -> G28
│   │
│   ├── AXIS_ALIGNMENT (메뉴별 X축 진입):
│   │   [Positioning] G1 X[x_val]  # 수블라키: 2000, 투움: 2400, 룰라: 2800, 비프샤슬릭: 3300, 치킨샤슬릭: 3600
│   │   [G-code Flow]
│   │   |- G38 X200 F200   # PC6 센서 감지 탐색
│   │   |- G92 X0          # 기준점 리셋
│   │   |- G1 X-20 F1000   # 20스텝 안전 마진 후퇴
│   │   |- G90             # 절대 좌표계 복귀
│   │   |- G1 Z2000 -> G1 Y2000 -> G1 Z200
│   │   |- G40             # PD2 프로브 센서 접촉 시까지 하강
│   │   |- M800 P4 S1      # 공압 파지 ON
│   │   |- M800 P5 S1      # 보조 예압 체결 ON
│   │   `- G28 Z Y         # 상승 후 회전 원점 복귀
│   │
│   ├── BRANCH_RULES (냉장고 도어 닫기):
│   │   ├── [RULE_A] IF target_item["name"] in ["수블라키", "투움"]
│   │   │   └── ACTION_SEQUENCE: M128 P0 -> M119
│   │   └── [RULE_B] IF target_item["name"] in ["룰라", "비프샤슬릭", "치킨샤슬릭"]
│   │       └── ACTION_SEQUENCE: M128 P1 -> M119
│   │
│   └── COMMON_ACTIONS (종료):
│       [Python] is_unit1_busy = False; target_item["status"] = "1단계:완료대기"
│
├── 2단계 unit change (대상: stm_unit_1, stm_unit_2 연동)
│   ├── 2-1단계: stm_unit_2 도킹 접근
│   │   ├── EXEC_TRIGGER:
│   │   │   [조건] 11분 30초 초과 요리 부재 && 1단계 완료 항목 존재 && Unit 2 유휴 && stm1_pd2 감지 && stm1_pc7 미감지
│   │   │   [Python] not has_cooking_over_limit() and (get_ready_stage1_item() is not None) and not is_unit2_busy and (sensor_states["stm1_pd2"] == "triggered") and (sensor_states["stm1_pc7"] == "no trigger")
│   │   ├── SENSOR_READ:
│   │   │   [G-code] M119
│   │   │   [Target Pins] (stm_2) PC6, PB9
│   │   └── ACTIONS:
│   │       [Python] is_unit2_busy = True; unit2_at_prepick_pos = False; item["status"] = "2단계:Change"
│   │       [G-code] G1 X(b1_x + 2500) -> G38 X200 F200 -> G92 X0 -> G1 X-20 F1000 -> G90
│   │
│   ├── 2-2단계: stm_unit_1 도킹 하강
│   │   ├── EXEC_TRIGGER: 2-1단계 이동 완료 수신 (OK)
│   │   └── ACTIONS: [G-code] (stm_1) G40  # Z축 PC7 도킹 센서 접촉까지 전진
│   │
│   ├── 2-3단계: stm_unit_2 파지 인계
│   │   ├── EXEC_TRIGGER: 2-2단계 도킹 완료 수신 (OK)
│   │   └── ACTIONS: [G-code] (stm_2) M800 P0 S1 -> G4 P1000  # Unit 2 그리퍼 파지 체결
│   │
│   └── 2-4단계: stm_unit_1 파지 해제 및 원점 복귀
│       ├── EXEC_TRIGGER: 2-3단계 파지 완료 수신 (OK)
│       └── ACTIONS:
│           [G-code] (stm_1) M800 P0 S0 -> M800 P1 S0 -> G4 P2000 -> G28
│           [Python] sensor_states["stm1_pc7"] = "triggered"; item["status"] = "2단계:완료대기"; is_unit2_busy = False
│
├── 3단계 cook and place (대상: stm_unit_2)
│   ├── EXEC_TRIGGER:
│   │   [조건] 11분 30초 초과 요리 부재 && 2단계 완료 항목 존재 && stm1_pc7 감지 && 앞면 플레이트 내 잔여 체류시간 20초 이상 슬롯 확보
│   │   [Python] not has_cooking_over_limit() and any(item["status"] == "2단계:완료대기" for item in active_orders) and (sensor_states["stm1_pc7"] == "triggered") and (get_empty_heat_slot_in_front_plate() is not None) and not is_unit2_busy
│   │
│   ├── SENSOR_READ:
│   │   [G-code] M119
│   │   [Target Pins] (stm_2) PA9, PA10, PB9, PC5
│   │
│   └── ACTIONS:
│       [Python] is_unit2_busy = True; unit2_at_prepick_pos = False; item["assigned_slot"] = target_slot; item["status"] = "3단계:CookPlace"; heat_units[target_slot]["status"] = "reserved"
│       [G-code Flow]
│       |- G1 X(target_slot * 200)   # 지정된 슬롯 좌표로 정밀 수평 이송
│       |- G1 Z1500 Y1500           # 투입 위치 하강 및 회전 진입
│       |- M800 P0 S0               # Unit 2 그리퍼 해제
│       |- G4 P1000                 # 1초 안정화 대기
│       |- M800 P2 S1               # Heat unit 락킹 실린더 고정 체결
│       `- G28 Z Y                  # 안전 고도 복귀 및 원점 정렬
│       [Python Completion]
│       |- is_unit2_busy = False; unit2_at_prepick_pos = True; sensor_states["stm1_pc7"] = "no trigger"
│       |- item["status"] = "4단계:조리중"; heat_units[target_slot]["status"] = "cooking"; heat_units[target_slot]["order"] = item
│       `- heat_units[target_slot]["total_cook_time" / "front_cook_time" / "back_cook_time" / "heat_unit_stay_time"] = 0.0 (4대 타이머 개시)
│
├── 4단계 go to cook (위상 반전) (대상: stm_unit_2)
│   ├── EXEC_TRIGGER:
│   │   [조건] Unit 2 유휴 && 플레이트 미반전 상태 && (HP1 또는 HP2의 위상 체류 타이머 >= 120.0초)
│   │   [Python] not is_unit2_busy and not (plate_flipping_lock[1] or plate_flipping_lock[2]) and (plate_phase_timer[1] >= TIMER_UNIT_STAY_MAX or plate_phase_timer[2] >= TIMER_UNIT_STAY_MAX)
│   │
│   ├── SENSOR_READ:
│   │   [G-code] M119
│   │   [Target Pins] (stm_2) PC6 (위상 판정 센서), PB13, PB14, PC8
│   │
│   ├── BRANCH_RULES:
│   │   ├── [CASE_A] IF (PC6: OPEN) -> Set 1 위상 반전
│   │   │   [G-code] M800 P7 S1 -> M103 P0 S2000 F2000 D0 -> M103 P1 S2000 F2000 D1 -> M800 P5 S0 -> M119
│   │   │   [State Transition] HP1: 앞면 -> 뒷면 / HP2: 뒷면 -> 앞면
│   │   └── [CASE_B] IF (PC6: CLOSED) -> Set 2 위상 반전
│   │       [G-code] M800 P5 S1 -> M103 P0 S2000 F2000 D1 -> M103 P1 S2000 F2000 D0 -> M800 P7 S0 -> M119
│   │       [State Transition] HP1: 뒷면 -> 앞면 / HP2: 앞면 -> 뒷면
│   │
│   └── ACTIONS (완료 처리):
│       [Python]
│       |- plate_flipping_lock[1] = plate_flipping_lock[2] = False; is_unit2_busy = False
│       |- plate_phase_timer[1] = plate_phase_timer[2] = 0.0
│       `- for slot in cooking_slots: heat_units[slot]["heat_unit_stay_time"] = 0.0 (4번 체류 타이머 리셋)
│
├── 5단계 cook and place 배출 (대상: stm_unit_2)
│   ├── EXEC_TRIGGER:
│   │   [조건] 총 조리시간 >= 710.0초 (11분 50초) && 대상 슬롯이 앞면 위치 && Unit 2 프리픽 위치 && stm2_pc6 대기 상태 && stm1_pc7 안전 상태
│   │   [Python] not is_unit2_busy and (info["total_cook_time"] >= TIMER_STAGE5_TRIGGER) and (plate_current_side[info["plate_id"]] == "front") and unit2_at_prepick_pos and (sensor_states["stm2_pc6"] == "no trigger") and (sensor_states["stm1_pc7"] == "no trigger")
│   │
│   ├── SENSOR_READ:
│   │   [G-code] M119
│   │   [Target Pins] (stm_2) PA9, PA10, PB9, PC5
│   │
│   └── ACTIONS:
│       [Python] is_unit2_busy = True; unit2_at_prepick_pos = False; info["status"] = "finished"; order["status"] = "5단계:완성배출"
│       [G-code Flow]
│       |- G1 X(slot_id * 200)       # 완성된 조리 슬롯으로 접근
│       |- G28 Y -> G28 Z            # Y/Z축 정렬
│       |- M800 P0 S1                # 조리물 파지 ON
│       |- G1 Y1500 Z1500            # 충돌 방지 고도 상승
│       |- G28 X                     # 배출 기준 위치로 복귀
│       `- M800 P0 S0                # 그리퍼 해제 (배출 완료)
│       [Python Completion]
│       |- is_unit2_busy = False; unit2_at_prepick_pos = True
│       |- info["status"] = "idle"; info["order"] = None; 4대 타이머 전체 0.0초 초기화
│       `- order["status"] = "6단계:접시적재" -> _handle_stage6_plate_batching(order) 호출
│
└── 6단계 finish stage (접시 공급 및 컨베이어 배출) (대상: stm_unit_3)
    ├── 6-1단계: 접시 사전 투입 (사전 대기)
    │   ├── EXEC_TRIGGER:
    │   │   [조건] Unit 3 유휴 && 슬롯 중 총 조리시간 >= 660.0초(11분) 요리 발생 && 접시 미장전 상태
    │   │   [Python] not is_unit3_busy and (unit3_stage6_status == "idle") and any(info["total_cook_time"] >= TIMER_STAGE6_TRIGGER for info in heat_units.values())
    │   ├── BRANCH_RULES (접시 잔여 수량 관리: 변수 3):
    │   │   ├── [CASE_A] IF dish_stock["tim3_ch3"] > 0
    │   │   │   └── ACTION: dish_stock["tim3_ch3"] -= 1; G-code: G39 P0 S20000 F400 -> M103 P3 S2000 F2000 D1 -> G1 Z2000
    │   │   ├── [CASE_B] IF dish_stock["tim3_ch3"] == 0 and dish_stock["tim3_ch4"] > 0
    │   │   │   └── ACTION: dish_stock["tim3_ch4"] -= 1; G-code: G39 P1 S20000 F400 -> M103 P3 S2000 F2000 D1 -> G1 Z2000
    │   │   └── [CASE_C] IF dish_stock 전부 소진
    │   │       └── ACTION: 콘솔 및 GUI 경고 발생 -> G4 P1000
    │   └── ACTIONS: is_unit3_busy = True; unit3_stage6_status = "plate_fed"
    │
    ├── 6-2단계: 접시 수령 및 조리 완료 대기 위치 격리
    │   ├── EXEC_TRIGGER: 6-1단계 G-code 실행 완료 (OK)
    │   └── ACTIONS:
    │       [G-code] G1 Z200 -> M119
    │       [Python] is_unit3_busy = False; unit3_stage6_status = "waiting_dish"
    │
    └── 6-3단계: 테이블별 최종 배출 및 배칭 판정 (변수 2)
        ├── EXEC_TRIGGER:
        │   [조건] 5단계 배출 요리가 접시에 적재되었을 때 아래 분기 조건 충족 시
        │   [Python] (current_serving_plate["loaded_count"] >= 3) or (same_seq_remaining == 0) or (새 주문열 요리 도착)
        ├── BRANCH_RULES (변수 2 배칭 판정):
        │   ├── [RULE 1: 정량 적재] 동일 주문열 요리가 누적 3개 도달 시 즉시 배출
        │   ├── [RULE 2: 잔여 종결] 동일 주문열의 남은 조리물이 0개이면 3개 미만(1~2개)이라도 즉시 배출
        │   └── [RULE 3: 열 분리] 다른 주문열의 요리가 도착하면 기존 접시 강제 배출 후 신규 접시 발번
        └── ACTIONS:
            [Python] is_unit3_busy = True; unit3_stage6_status = "delivering"
            [G-code] G1 X2000 -> G1 Y1500 -> G1 Z0 -> M103 P3 S(table_num * 1500) F2000 D1
            [Python Completion]
            |- is_unit3_busy = False; unit3_stage6_status = "idle"
            `- current_serving_plate = None (배칭 완료 리셋)

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
 
ㅖㅠ
