import streamlit as st
import pandas as pd
import re


# =====================================
# 페이지 설정
# =====================================

st.set_page_config(
    page_title="이화인의 공강을 설계하다",
    page_icon="🎓",
    layout="centered"
)


# =====================================
# 데이터 불러오기
# =====================================

df = pd.read_csv("places.csv", encoding="cp949")


# =====================================
# OO / O / 빈칸을 점수로 변환
# OO = 매우 적합
# O = 적합
# 빈칸/X = 부적합
# =====================================

def make_score(value):
    if value == "OO":
        return 2
    elif value == "O":
        return 1
    else:
        return 0


df["solo_score"] = df["solo_raw"].apply(make_score)
df["study_score"] = df["study_raw"].apply(make_score)
df["sleep_score"] = df["sleep_raw"].apply(make_score)


# 숫자형으로 변환
df["price"] = pd.to_numeric(
    df["price"],
    errors="coerce"
)

df["walking_time"] = pd.to_numeric(
    df["walking_time"],
    errors="coerce"
)


# 같은 장소가 중복으로 들어있는 경우 제거
df = df.drop_duplicates(
    subset=["name", "category"]
)


# =====================================
# 자연어 입력 해석
# =====================================

def parse_user_text(text):

    # 기본값
    gap_time = 120
    total_budget = 15000
    want_study = False


    # ---------------------------------
    # 시간 해석
    # ---------------------------------

    # "2시간"
    hour_match = re.search(
        r"(\d+)\s*시간",
        text
    )

    # "30분"
    minute_match = re.search(
        r"(\d+)\s*분",
        text
    )


    if hour_match:
        gap_time = (
            int(hour_match.group(1)) * 60
        )


    if minute_match:
        gap_time += int(
            minute_match.group(1)
        )


    # "120분"처럼 분만 입력한 경우
    if not hour_match and minute_match:

        gap_time = int(
            minute_match.group(1)
        )


    # ---------------------------------
    # 예산 해석
    # ---------------------------------

    # "15000원"
    # "15,000원"
    budget_match = re.search(
        r"(\d[\d,]*)\s*원",
        text
    )


    if budget_match:

        budget_text = (
            budget_match.group(1)
            .replace(",", "")
        )

        total_budget = int(
            budget_text
        )


    # ---------------------------------
    # 공부 여부
    # ---------------------------------

    if "공부" in text or "카공" in text:

        want_study = True


    return (
        gap_time,
        total_budget,
        want_study
    )


# =====================================
# 공강 코스 추천 함수
# =====================================

def recommend_course(
    gap_time,
    total_budget,
    max_walk,
    want_study
):

    # 식당
    restaurants = df[
        df["category"] == "식당"
    ].copy()


    # 카페
    cafes = df[
        df["category"] == "카페"
    ].copy()


    # ---------------------------------
    # 기본 조건 필터링
    # ---------------------------------

    restaurants = restaurants[
        (restaurants["price"] <= total_budget)
        &
        (restaurants["walking_time"] <= max_walk)
    ]


    cafes = cafes[
        (cafes["price"] <= total_budget)
        &
        (cafes["walking_time"] <= max_walk)
    ]


    courses = []


    # =================================
    # 식당 + 카페 조합
    # =================================

    for _, restaurant in restaurants.iterrows():

        for _, cafe in cafes.iterrows():

            # ---------------------------------
            # 총 비용
            # ---------------------------------

            total_price = (
                restaurant["price"]
                + cafe["price"]
            )


            # ---------------------------------
            # 전체 예산 초과 시 제외
            # ---------------------------------

            if total_price > total_budget:
                continue


            # ---------------------------------
            # 총 이동시간
            # ---------------------------------

            total_walk = (
                restaurant["walking_time"]
                + cafe["walking_time"]
            )


            # ---------------------------------
            # 예상 소요시간
            # 식사 50분 + 카페 40분 + 이동시간
            # ---------------------------------

            estimated_time = (
                total_walk
                + 50
                + 40
            )


            # ---------------------------------
            # 공강 시간 초과 시 제외
            # ---------------------------------

            if estimated_time > gap_time:
                continue


            # ---------------------------------
            # 예산 점수
            # 저렴할수록 높은 점수
            # ---------------------------------

            budget_score = (
                total_budget - total_price
            ) / 1000


            # ---------------------------------
            # 이동 점수
            # 가까울수록 높은 점수
            # ---------------------------------

            walk_score = -total_walk


            # ---------------------------------
            # 카공 적합도
            # ---------------------------------

            study_score = 0


            if want_study:

                if cafe["study_score"] == 2:

                    study_score = 10

                elif cafe["study_score"] == 1:

                    study_score = 5

                else:

                    study_score = 0


            # ---------------------------------
            # 최종 추천 점수
            # ---------------------------------

            score = (
                budget_score
                + walk_score
                + study_score
            )


            # ---------------------------------
            # 결과 저장
            # ---------------------------------

            courses.append({

                "restaurant":
                    restaurant["name"],

                "cafe":
                    cafe["name"],

                "total_price":
                    total_price,

                "total_walk":
                    total_walk,

                "estimated_time":
                    estimated_time,

                "study_score":
                    cafe["study_score"],

                "score":
                    score
            })


    # =====================================
    # 추천 결과가 없는 경우
    # =====================================

    if len(courses) == 0:

        return pd.DataFrame()


    # =====================================
    # DataFrame 생성
    # =====================================

    result = pd.DataFrame(
        courses
    )


    # =====================================
    # 추천 점수순 정렬
    # =====================================

    result = result.sort_values(
        "score",
        ascending=False
    )


    # =====================================
    # 식당 + 카페 중복 없이 3개 선택
    # =====================================

    selected = []

    used_restaurants = set()

    used_cafes = set()


    for _, row in result.iterrows():

        # 이미 추천한 식당이면 제외
        if row["restaurant"] in used_restaurants:
            continue


        # 이미 추천한 카페면 제외
        if row["cafe"] in used_cafes:
            continue


        # 추천 목록에 추가
        selected.append(row)


        # 사용한 장소 기록
        used_restaurants.add(
            row["restaurant"]
        )

        used_cafes.add(
            row["cafe"]
        )


        # 최대 3개
        if len(selected) == 3:
            break


    return pd.DataFrame(
        selected
    )


# =====================================
# 화면
# =====================================

st.title(
    "🎓 이화인의 공강을 설계하다"
)


st.write(
    "공강 시간과 하고 싶은 일을 자유롭게 입력하면 "
    "나에게 맞는 공강 코스를 추천해드려요."
)


# =====================================
# 자연어 입력
# =====================================

user_text = st.text_area(

    "💬 공강 계획을 자유롭게 입력해주세요",

    placeholder=(
        "예시: 오늘 2시간 공강인데 "
        "친구랑 밥 먹고 카페에서 공부하고 싶어. "
        "15000원 정도 생각하고 있어."
    ),

    height=120
)


# =====================================
# 추천 버튼
# =====================================

if st.button(
    "✨ 공강 코스 추천받기",
    use_container_width=True
):

    if user_text.strip() == "":

        st.warning(
            "공강 계획을 입력해주세요!"
        )

    else:

        # =================================
        # 자연어 → 조건 변환
        # =================================

        (
            gap_time,
            total_budget,
            want_study
        ) = parse_user_text(
            user_text
        )


        # =================================
        # AI가 이해한 계획
        # =================================

        st.subheader(
            "🤖 AI가 이해한 공강 계획"
        )


        col1, col2, col3 = st.columns(3)


        with col1:

            st.metric(
                "⏰ 공강 시간",
                f"{gap_time}분"
            )


        with col2:

            st.metric(
                "💰 예산",
                f"{total_budget:,}원"
            )


        with col3:

            if want_study:

                study_text = "카공 희망"

            else:

                study_text = "카공 조건 없음"


            st.metric(
                "📚 활동",
                study_text
            )


        st.divider()


        # =================================
        # 추천 실행
        # =================================

        result = recommend_course(

            gap_time=gap_time,

            total_budget=total_budget,

            max_walk=5,

            want_study=want_study
        )


        # =================================
        # 추천 결과
        # =================================

        if result.empty:

            st.error(
                "조건에 맞는 공강 코스를 찾지 못했어요."
            )

            st.info(
                "공강 시간을 늘리거나 "
                "예산을 조금 높여보세요!"
            )


        else:

            st.subheader(
                "✨ 추천 공강 코스"
            )


            # =================================
            # 추천 결과 출력
            # =================================

            rank_emoji = [
                "🥇",
                "🥈",
                "🥉"
            ]


            for i, (_, row) in enumerate(
                result.iterrows()
            ):

                st.markdown(
                    f"### {rank_emoji[i]} "
                    f"{row['restaurant']} → "
                    f"{row['cafe']}"
                )


                # ---------------------------------
                # 추천 이유
                # ---------------------------------

                if want_study:

                    if row["study_score"] == 2:

                        reason = (
                            "식사 후 카공하기 좋은 "
                            "조합이에요."
                        )

                    elif row["study_score"] == 1:

                        reason = (
                            "식사 후 공부까지 가능한 "
                            "공강 코스예요."
                        )

                    else:

                        reason = (
                            "식사와 카페를 함께 "
                            "이용할 수 있는 코스예요."
                        )

                else:

                    reason = (
                        "공강 시간과 예산을 고려한 "
                        "추천 코스예요."
                    )


                st.write(
                    f"💡 {reason}"
                )


                # ---------------------------------
                # 세부 정보
                # ---------------------------------

                col1, col2, col3 = st.columns(3)


                with col1:

                    st.metric(
                        "💰 예상 비용",
                        f"{int(row['total_price']):,}원"
                    )


                with col2:

                    st.metric(
                        "🚶 이동",
                        f"{int(row['total_walk'])}분"
                    )


                with col3:

                    st.metric(
                        "⏱ 예상 소요",
                        f"{int(row['estimated_time'])}분"
                    )


                # ---------------------------------
                # 카공 적합도
                # ---------------------------------

                if want_study:

                    if row["study_score"] == 2:

                        st.success(
                            "📚 카공 적합도: 매우 높음"
                        )

                    elif row["study_score"] == 1:

                        st.info(
                            "📚 카공 적합도: 가능"
                        )

                    else:

                        st.warning(
                            "📚 카공 적합도: 낮음"
                        )


                st.divider()