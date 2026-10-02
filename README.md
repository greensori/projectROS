조리 프로세스는 크게 총 5단계로 구성이 되는거고

아래 순서대로 일이 처리되는 것이야

조리단계에서 각 메뉴들은 총 5개의 타이머를 가져야해

1. 총 조리시간을 기록하는 타이머(최대 12분, 하지만 초과할수 있음
2. 앞면의 총 조리시간을 기록하는 타이머(최대 6분, 하지만 초과할수 있음)
3. 뒷면의 총 조리시간을 기록하는 타이머(최대 6분, 하지만 초과할수 있음)
4. heat unit 조리시간을 기록하는 타이머(최대 2분, 하지만 초과할수 있음)


자동화 설비 요약 
이송유닛1. XYZ 이송 유닛 (Z축 말단에 PD2입력센서 존재, G40과 연동하여 물건 탐지시까지 이동 수행)
오픈유닛1. tim3
├── (stm_1)
│   ├── stm_unit_1. XYZ 이송 유닛 (Z축 말단에 PD2입력센서 존재, G40과 연동하여 물건 탐지시까지 이동 수행)
│   │   ├── (Z축 말단에 PD2입력센서 존재, G40과 연동하여 물건 탐지시까지 이동 수행)
│   │   ├── (X축 PC6입력센서 존재, G38과 연동하여 물건 탐지시까지 이동 수행)
│   ├── OPENER_1. tim3 ch1
│   ├── OPENER_2. tim3 ch2
│   ├── DISH_Transfer_X. tim3 ch3
│   ├── DISH_Transfer_Y. tim3 ch4
│   ├── rodless_unit_1. (시작리미트 PC4, 엔드리미트 PC5)

├── (stm_2)
│   ├── stm_unit_2. XYZ 이송 유닛
│   │   ├── (테이블상단에 (stm1, PC7)입력센서 존재, G40과 연동하여 물건 탐지시까지 이동 수행)
│   │   ├── (X축 PC6입력센서 존재, G38과 연동하여 물건 탐지시까지 이동 수행)
│   ├── PLATE_changer_1. tim3 ch1 (정방향리미트 PA9, 역방향리미트 PB9)
│   ├── PLATE_changer_2. tim3 ch2 (정방향리미트 PA10, 역방향리미트 PC5)
│   ├── Ignight_starter_1. tim3 ch3
│   ├── Ignight_starter_2. tim3 ch4



조리 프로세스
├── 1단계 pick and place (stm_unit_1)
│   ├── EXEC_TRIGGER: 주문 대기열 존재 && 이전 공정 완료
│   ├── SENSOR_READ: M119 (타겟 핀: PD2, PC7, PC6)
│   │
│   ├── BRANCH_RULES:
│   │   ├── [RULE_A] IF (PD2: OPEN && 주문메뉴('수블라키', '투움')
│   │   │   └── ACTION_SEQUENCE:
│   │   │       |- M103 P0 S2000 F2000 D0   # 냉장고 오픈
│   │   │       |- M103 P2 S2000 F2000 D0   # 접시 축 가동
│   │   │       `- G28                      # 시작전 복귀
│   │   │    
│   │   ├── [RULE_B] IF (PD2: OPEN && 주문메뉴('룰라', '비프샤슬릭', '치킨샤슬릭')
│   │   │   └── ACTION_SEQUENCE:
│   │   │       |- M103 P1 S2000 F2000 D0   # 냉장고 오픈
│   │   │       |- M103 P3 S2000 F2000 D0   # 접시 축 가동
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
│       │       |- G38 X200 F200              # x축 센서탐지(PC6)까지 이동
│       │       |- G92 X0                # x축 재설정
│       │       |- G1 X-20 F1000             # x축 조정이동
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
└── 5단계 cook and place (stm_unit_2) 
    ├── EXEC_TRIGGER: 총조리시간이 11분 50초을 초과한 요리가 있는 경우 그 위치로 이동 && pc6센서가 idle상태일것 
    ├── SENSOR_READ: M119 (타겟 핀: PD2, PC7, PC6)
    │
    └── COMMON_ACTIONS:
        |- G1 X()           # heat unit 자리 : 1번(x200), 2번(x400), .... 14번(x2800)
        |- G28 Y
        |- G28 Z
        |- M800 P0 S1
        |- G1 Y1500 Z1500
        |- G28 X
        `- M800 P0 S0


조리 프로세스 상태 머신 및 파이썬 매핑 명세서
====================================================================================================

├── 1단계 pick and place (대상: stm_unit_1)
│   ├── EXEC_TRIGGER:
│   │   [조건] 주문 대기열 존재 && 이전 공정 완료 (Unit 1 유휴)
│   │   [Python] any(item["status"] == "대기" for item in active_orders) and not is_unit1_busy
│   │
│   ├── SENSOR_READ:
│   │   [동작] M119 수신 파싱 (타겟: stm1_pd2, stm1_pc7, stm1_pc6)
│   │   [Python] sensor_states["stm1_pd2"], sensor_states["stm1_pc7"], sensor_states["stm1_pc6"]
│   │
│   ├── PRE_CHECK_INTERLOCK:
│   │   [조건] Unit 1 주변 간섭 방지 (PC7, PD2 미감지 상태)
│   │   [Python] sensor_states["stm1_pc7"] == "no trigger" and sensor_states["stm1_pd2"] == "no trigger"
│   │
│   ├── BRANCH_RULES (냉장고 및 접시축 오픈):
│   │   ├── [RULE_A] IF (PD2: OPEN && 주문메뉴 in ('수블라키', '투움'))
│   │   │   [Python] sensor_states["stm1_pd2"] == "no trigger" and item["name"] in ["수블라키", "투움"]
│   │   │   └── ACTION_SEQUENCE:
│   │   │       |- M103 P0 S2000 F2000 D0    # 1번 냉장고 오픈
│   │   │       |- M103 P2 S2000 F2000 D0    # 접시 축 1 가동
│   │   │       `- G28                       # 시작 전 홈 복귀
│   │   │
│   │   ├── [RULE_B] IF (PD2: OPEN && 주문메뉴 in ('룰라', '비프샤슬릭', '치킨샤슬릭'))
│   │   │   [Python] sensor_states["stm1_pd2"] == "no trigger" and item["name"] in ["룰라", "비프샤슬릭", "치킨샤슬릭"]
│   │   │   └── ACTION_SEQUENCE:
│   │   │       |- M103 P1 S2000 F2000 D0    # 2번 냉장고 오픈
│   │   │       |- M103 P3 S2000 F2000 D0    # 접시 축 2 가동
│   │   │       `- G28                       # 시작 전 홈 복귀
│   │   │
│   │   └── [RULE_C] IF (PD2: CLOSED / 감지 상태)
│   │       [Python] sensor_states["stm1_pd2"] == "triggered"
│   │       └── ACTION_SEQUENCE:
│   │           |- G4 P1000                  # 1초 지연
│   │           `- M119                      # 센서 재조회 (인터록 해제 대기)
│   │
│   ├── BRANCH_RULES (메뉴별 X축 픽업 위치 이동):
│   │   [Python] target_x = {"수블라키": 2000, "투움": 2400, "룰라": 2800, "비프샤슬릭": 3300, "치킨샤슬릭": 3600}[item["name"]]
│   │   ├── [CASE_A] item["name"] == "수블라키"   └── G1 X2000
│   │   ├── [CASE_B] item["name"] == "투움"       └── G1 X2400
│   │   ├── [CASE_C] item["name"] == "룰라"       └── G1 X2800
│   │   ├── [CASE_D] item["name"] == "비프샤슬릭" └── G1 X3300
│   │   └── [CASE_E] item["name"] == "치킨샤슬릭" └── G1 X3600
│   │
│   ├── COMMON_ACTIONS (재료 파지 및 리프팅):
│   │   [Python] execute_gcode_sequence(unit1_slot, [...])
│   │   |- G1 X200                           # 미세 조정 이동
│   │   |- G1 Z2000
│   │   |- G1 Y2000
│   │   |- G1 Z200
│   │   |- G40                               # Z축 리미트 센서 접촉까지 전진
│   │   |- M800 P4 S1                        # 공압 그리퍼 흡착/전진 1
│   │   |- M800 P5 S1                        # 공압 그리퍼 흡착/전진 2
│   │   `- G28 Z Y                           # Z/Y축 원점 복귀
│   │
│   ├── BRANCH_RULES (냉장고 도어 닫기):
│   │   ├── [RULE_A] IF (PD2: OPEN && 주문메뉴 in ('수블라키', '투움'))
│   │   │   [Python] sensor_states["stm1_pd2"] == "no trigger" and item["name"] in ["수블라키", "투움"]
│   │   │   └── ACTION_SEQUENCE:
│   │   │       |- M103 P0 S2000 F2000 D1    # 1번 냉장고 닫기
│   │   │       `- M119
│   │   │
│   │   └── [RULE_B] IF (PD2: OPEN && 주문메뉴 in ('룰라', '비프샤슬릭', '치킨샤슬릭'))
│   │       [Python] sensor_states["stm1_pd2"] == "no trigger" and item["name"] in ["룰라", "비프샤슬릭", "치킨샤슬릭"]
│   │       └── ACTION_SEQUENCE:
│   │           |- M103 P1 S2000 F2000 D1    # 2번 냉장고 닫기
│   │           `- M119
│   │
│   └── POST_STATE_UPDATE:
│       [Python] is_unit1_busy = False
│       [Python] item["status"] = "1단계:완료대기"
│       [Python] sensor_states["stm1_pd2"] = "triggered"   # 도킹 위치 도착 모사
│
│
├── 2-1단계 unit change (대상: stm_unit_2 접근)
│   ├── EXEC_TRIGGER:
│   │   [조건] 11분 30초(690초) 초과 요리 부재 && 1단계 완료대기 항목 존재 && Unit 2 유휴
│   │   [Python] not any(u["total_cook_time"] >= 690.0 for u in heat_units.values())
│   │   [Python] and any(item["status"] == "1단계:완료대기" for item in active_orders)
│   │   [Python] and not is_unit2_busy
│   │
│   ├── SENSOR_READ:
│   │   [동작] Unit 2 위치 및 센서 확인 (PD2, PC7, PC6)
│   │   [Python] sensor_states["stm2_pc6"], sensor_states["stm1_pc7"], sensor_states["stm1_pd2"]
│   │
│   └── BRANCH_RULES:
│       ├── [RULE_A] IF (PC6: OPEN / no trigger) -> 접근 모션 실행
│       │   [Python] sensor_states["stm2_pc6"] == "no trigger"
│       │   [Python] target_x = item["b1_x"] + 2500
│       │   └── ACTION_SEQUENCE:
│       │       |- G1 X{target_x}            # Unit 1 X위치 + 2500 좌표로 Unit 2 이동
│       │       `- G38                       # X축 맞물림 센서 접촉까지 감속 탐지
│       │
│       └── [RULE_B] IF (PC6: CLOSED / triggered) -> 접근 차단 및 대기
│           [Python] sensor_states["stm2_pc6"] == "triggered"
│           └── ACTION_SEQUENCE:
│               |- G4 P1000
│               `- M119
│
│
├── 2-2단계 unit change (대상: stm_unit_1 Z축 도킹 전진)
│   ├── EXEC_TRIGGER:
│   │   [조건] 2-1단계 Unit 2 접근 G38 완료 콜백
│   │   [Python] on_step2_1_done callback
│   │
│   └── COMMON_ACTIONS:
│       [Python] execute_gcode_sequence(unit1_slot, ["G40"])
│       `- G40                               # Z축 도킹 센서(PC6) 접촉 시까지 이송유닛 쪽 전진
│
│
├── 2-3단계 unit change (대상: stm_unit_2 파지)
│   ├── EXEC_TRIGGER:
│   │   [조건] 2-2단계 Unit 1 G40 전진 완료 콜백
│   │   [Python] on_step2_2_done callback
│   │
│   └── COMMON_ACTIONS:
│       [Python] execute_gcode_sequence(unit2_slot, ["M800 P0 S1", "G4 P1000"])
│       |- M800 P0 S1                        # Unit 2 메인 그리퍼 파지 작동
│       `- G4 P1000                          # 1초 물리적 흡착/체결 대기
│
│
├── 2-4단계 unit change (대상: stm_unit_1 해제 및 홈 복귀)
│   ├── EXEC_TRIGGER:
│   │   [조건] 2-3단계 Unit 2 파지 완료 콜백
│   │   [Python] on_step2_3_done callback
│   │
│   ├── COMMON_ACTIONS:
│   │   [Python] execute_gcode_sequence(unit1_slot, ["M800 P0 S0", "M800 P1 S0", "G4 P2000", "G28"])
│   │   |- M800 P0 S0                        # Unit 1 그리퍼 릴리즈
│   │   |- M800 P1 S0
│   │   |- G4 P2000                          # 2초 릴리즈 안정화 대기
│   │   `- G28                               # Unit 1 완전 원점 복귀 (다음 요리 픽업 준비 완료)
│   │
│   └── POST_STATE_UPDATE:
│       [Python] sensor_states["stm1_pc7"] = "triggered"   # Unit 1 복귀 및 인계 완료 플래그
│       [Python] item["status"] = "2단계:완료대기"
│       [Python] is_unit2_busy = False                     # 3단계 즉시 진입 유도
│
│
├── 3단계 cook and place (대상: stm_unit_2 조리대 안착)
│   ├── EXEC_TRIGGER:
│   │   [조건] 11분 30초(690초) 초과 요리 부재 &&
│   │          2단계 완료대기 항목 존재 &&
│   │          stm1_pc7 == triggered &&
│   │          1~14번 중 앞면(front) 빈 슬롯 존재 &&
│   │          해당 플레이트 위상 반전(2분 만료)까지 남은 시간 >= 20초
│   │   [Python] not has_cooking_over_limit()
│   │   [Python] and item["status"] == "2단계:완료대기"
│   │   [Python] and sensor_states["stm1_pc7"] == "triggered"
│   │   [Python] and target_slot is not None (get_empty_heat_slot_in_front_plate())
│   │
│   ├── SENSOR_READ:
│   │   [동작] 조리대 영역 센서 확인
│   │   [Python] M119 (타겟: PA9, PA10, PB9, PC5)
│   │
│   ├── COMMON_ACTIONS:
│   │   [Python] target_x = target_slot * 200
│   │   [Python] execute_gcode_sequence(unit2_slot, [f"G1 X{target_x}", "G1 Z1500 Y1500", "M800 P0 S0", "G4 P1000", "M800 P2 S1", "G28 Z Y"])
│   │   |- G1 X{target_x}                    # 해당 슬롯 X 좌표 이동 (slot_id * 200)
│   │   |- G1 Z1500 Y1500                    # 슬롯 상단 하강
│   │   |- M800 P0 S0                        # Unit 2 그리퍼 해제 (고기 안착)
│   │   |- G4 P1000                          # 1초 안착 대기
│   │   |- M800 P2 S1                        # 고정/압착 공압 실린더 작동
│   │   `- G28 Z Y                           # Z/Y축 원점 복귀
│   │
│   └── POST_STATE_UPDATE:
│       [Python] sensor_states["stm1_pc7"] = "no trigger"
│       [Python] heat_units[target_slot]["status"] = "cooking"
│       [Python] heat_units[target_slot]["total_cook_time"] = 0.0
│       [Python] heat_units[target_slot]["heat_unit_stay_time"] = 0.0
│       [Python] item["status"] = "4단계:조리중"
│       [Python] is_unit2_busy = False
│
│
├── 4단계 go to cook (대상: stm_unit_2 플레이트 위상 회전)
│   ├── EXEC_TRIGGER:
│   │   [조건] 체류 타이머(plate_phase_timer) >= 120.0초 (2분 만료) && Unit 2 유휴 && 락 미체결
│   │   [Python] (plate_phase_timer[1] >= 120.0 or plate_phase_timer[2] >= 120.0)
│   │   [Python] and not is_unit2_busy and not plate_flipping_lock[1]
│   │
│   ├── SENSOR_READ:
│   │   [동작] 위상 센서 상태 판정
│   │   [Python] sensor_states["stm2_pc6"] (또는 plate_current_side[1] == "front")
│   │
│   └── BRANCH_RULES:
│       ├── [CASE_A] IF (PC6: OPEN / HP1 현재 앞면 상태) -> 명령어 Set 1 송출
│       │   [Python] plate_current_side[1] == "front" (목표: HP1 -> back, HP2 -> front)
│       │   └── ACTION_SEQUENCE:
│       │       |- M800 P7 S1                # 플레이트 락 해제
│       │       |- M103 P0 S2000 F2000 D0.   # HP1 위상 반전 (앞 -> 뒤)
│       │       |- M103 P1 S2000 F2000 D1.   # HP2 위상 반전 (뒤 -> 앞)
│       │       |- M800 P5 S0                # 락 체결
│       │       `- M119
│       │
│       └── [CASE_B] IF (PC6: CLOSED / HP1 현재 뒷면 상태) -> 명령어 Set 2 송출
│           [Python] plate_current_side[1] == "back" (목표: HP1 -> front, HP2 -> back)
│           └── ACTION_SEQUENCE:
│               |- M800 P5 S1                # 플레이트 락 해제
│               |- M103 P0 S2000 F2000 D1.   # HP1 위상 반전 (뒤 -> 앞)
│               |- M103 P1 S2000 F2000 D0.   # HP2 위상 반전 (앞 -> 뒤)
│               |- M800 P7 S0                # 락 체결
│               `- M119
│
│   └── POST_STATE_UPDATE:
│       [Python] plate_current_side[1], plate_current_side[2] = to_side_1, to_side_2
│       [Python] plate_phase_timer[1] = 0.0, plate_phase_timer[2] = 0.0
│       [Python] for s in cooking_slots: heat_units[s]["heat_unit_stay_time"] = 0.0
│       [Python] is_unit2_busy = False
│
│
└── 5단계 cook and place / Finish (대상: stm_unit_2 완제 배출)
    ├── EXEC_TRIGGER:
    │   [조건] 슬롯 요리 총 조리시간 >= 710.0초 (11분 50초 초과) &&
    │          해당 Heat Unit이 앞면(front) &&
    │          stm2_pc6 센서 IDLE (no trigger) &&
    │          Unit 2 유휴 && Unit 2 픽업 전 대기 위치 만족
    │   [Python] info["total_cook_time"] >= 710.0
    │   [Python] and plate_current_side[info["plate_id"]] == "front"
    │   [Python] and sensor_states["stm2_pc6"] == "no trigger"
    │   [Python] and not is_unit2_busy and unit2_at_prepick_pos
    │
    ├── SENSOR_READ:
    │   [동작] 배출 전 배출 간섭 센서 확인 (PD2, PC7, PC6)
    │   [Python] M119 (타겟: stm1_pc7 == "no trigger")
    │
    ├── COMMON_ACTIONS:
    │   [Python] target_x = slot_id * 200
    │   [Python] execute_gcode_sequence(unit2_slot, [f"G1 X{target_x}", "G28 Y", "G28 Z", "M800 P0 S1", "G1 Y1500 Z1500", "G28 X", "M800 P0 S0"])
    │   |- G1 X{target_x}                    # 해당 슬롯 X 좌표 이동 (slot_id * 200)
    │   |- G28 Y                             # Y축 정렬
    │   |- G28 Z                             # Z축 하강 정렬
    │   |- M800 P0 S1                        # 완제 요리 파지 (그리퍼 ON)
    │   |- G1 Y1500 Z1500                    # 서빙 위치 상승 및 전진
    │   |- G28 X                             # 서빙 배출대 위치로 이동
    │   `- M800 P0 S0                        # 그리퍼 OFF (서빙 접시 배출)
    │
    └── POST_STATE_UPDATE:
        [Python] active_orders.remove(target_order)
        [Python] heat_units[slot_id]["status"] = "idle"
        [Python] heat_units[slot_id]["total_cook_time"] = 0.0
        [Python] is_unit2_busy = False
        [Python] unit2_at_prepick_pos = True
====================================================================================================

처리 순서 정리(우선순위)
├── 1순위 : 4단계 goto cook
│   ├── stm보드_2 (heat unit 1에서 조리중인 상태의 2분을 초과한경우 전체가 위상변화, heat unit 2또한 같음) 
│   │   |- 규칙1. heat unit1 과 heat unit2는 서로 위치가 반대임
│   │   |- 규칙2. 매 2분 마다 앞면 뒷면이 변화함
│   │   └- 실행
│   └── 
├── 2순위 : 1단계  #독립적으로 작동
│   ├── 조건1 : 주문완료되어 대기중인 요리가 있을 것
│   ├── 조건2 : stm보드 상 센서정보를 읽고, stm_unit_1(PC7, PD2) 센서가 no trigger 상태 
│   └── 실행
├── 3순위 : 5단계  # 조리 완료된 유닛은 빠르게 처리 되어야 함
│   ├── 조건1 : 타이머의 시간이 11분 30초을 초과한 요리가 있는경우(조리타이의 시간이 큰 것부터 우선적으로 처리)
│   └── 조건2 : stm보드 상 센서정보를 읽고, stm_unit_1(PC7) 센서가 no trigger 상태 
│   ├── 조건3 : 대상 heat unit의 상태가 앞면인 경우
│   ├── 조건4 : stm_unit_2가 픽업전 위치에 위치한 경우 
│   └── 실행
├── 4순위 : 2단계    #3단계 진행을 위한 선행 조건
│   ├── 조건1 : 요리 조리타이머가 11분 30초를 초과한 상태가 없을 것
│   ├── 조건2 : stm보드 상 센서정보를 읽고, stm_unit_1(PD2) 센서가 trigger 상태, stm_unit_1(PC7) 센서가 no trigger 상태 
│   ├── 조건3 : 1단계 공정이 완료대기 상태일것
│   └── 결과 : stm_unit_1(PC7)센서가 trigger 변화함
├── 5순위 : 3단계 
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
