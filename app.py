import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(
    page_title="기업가치 약식 평가계산기",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 사이드바 설정
st.sidebar.title("기업가치 약식 평가계산기")
st.sidebar.markdown("---")
pages = ["1. 비상장주식 평가", "2. 주식가치 결과", "3. 현시점 세금계산", "4. 미래 주식가치", "5. 미래 세금계산"]
page = st.sidebar.radio("페이지 선택", pages)

# 세션 상태 초기화 (값 유지를 위해)
if 'evaluated' not in st.session_state:
    st.session_state.evaluated = False
if 'future_evaluated' not in st.session_state:
    st.session_state.future_evaluated = False
if 'stock_value' not in st.session_state:
    st.session_state.stock_value = None
if 'future_stock_value' not in st.session_state:
    st.session_state.future_stock_value = None

# 숫자 형식화 함수
def format_number(num):
    return f"{int(num):,}"

# 세금 계산 함수
def calculate_tax_details(value, owned_shares, share_price):
    if not value:
        return None
    
    owned_value = value["ownedValue"]
    
    # 상속증여세 (40%)
    inheritance_tax = owned_value * 0.4
    
    # 양도소득세 (22%)
    acquisition_value = owned_shares * share_price
    transfer_profit = owned_value - acquisition_value
    transfer_tax = transfer_profit * 0.22
    
    # 청산소득세 계산
    corporate_tax = owned_value * 0.25
    after_tax_value = owned_value - corporate_tax
    liquidation_tax = after_tax_value * 0.154
    
    return {
        "inheritanceTax": inheritance_tax,
        "transferTax": transfer_tax,
        "corporateTax": corporate_tax,
        "liquidationTax": liquidation_tax,
        "acquisitionValue": acquisition_value,
        "transferProfit": transfer_profit,
        "afterTaxValue": after_tax_value,
        "totalTax": corporate_tax + liquidation_tax
    }

# 비상장주식 가치 계산 함수
def calculate_stock_value(total_equity, net_income1, net_income2, net_income3, shares, 
                         interest_rate, evaluation_method, owned_shares):
    # 1. 순자산가치 계산
    net_asset_per_share = total_equity / shares
    
    # 2. 영업권 계산
    weighted_income = (net_income1 * 3 + net_income2 * 2 + net_income3 * 1) / 6
    weighted_income_per_share = weighted_income / shares
    weighted_income_per_share_50 = weighted_income_per_share * 0.5
    equity_return = (total_equity * (interest_rate / 100)) / shares
    annuity_factor = 3.7908
    goodwill = max(0, (weighted_income_per_share_50 - equity_return) * annuity_factor)
    
    # 3. 순자산가치 + 영업권
    asset_value_with_goodwill = net_asset_per_share + goodwill
    
    # 4. 손익가치 계산
    income_value = weighted_income_per_share * (100 / interest_rate)
    
    # 5. 최종가치 계산
    if evaluation_method == '부동산 과다법인':
        # 부동산 과다법인
        stock_value = (asset_value_with_goodwill * 0.6) + (income_value * 0.4)
        net_asset_80_percent = net_asset_per_share * 0.8
        final_value = max(stock_value, net_asset_80_percent)
        method_text = '부동산 과다법인: (자산가치×0.6 + 수익가치×0.4)'
    elif evaluation_method == '순자산가치만 평가':
        # 순자산가치만 적용
        final_value = net_asset_per_share
        method_text = '순자산가치만 평가'
    else:
        # 일반법인
        stock_value = (income_value * 0.6) + (asset_value_with_goodwill * 0.4)
        net_asset_80_percent = net_asset_per_share * 0.8
        final_value = max(stock_value, net_asset_80_percent)
        method_text = '일반법인: (수익가치×0.6 + 자산가치×0.4)'
    
    # 총 가치
    total_value = final_value * shares
    owned_value = final_value * owned_shares
    
    # 증가율 계산
    increase_percentage = round((final_value / net_asset_per_share) * 100)
    
    return {
        "netAssetPerShare": net_asset_per_share,
        "assetValueWithGoodwill": asset_value_with_goodwill,
        "incomeValue": income_value,
        "finalValue": final_value,
        "totalValue": total_value,
        "ownedValue": owned_value,
        "methodText": method_text,
        "increasePercentage": increase_percentage,
        "weightedIncome": weighted_income
    }

# 미래 주식가치 계산 함수
def calculate_future_stock_value(stock_value, total_equity, shares, owned_shares, 
                               interest_rate, evaluation_method, growth_rate, future_years):
    if not stock_value:
        return None
    
    # 복리 성장률 적용
    growth_factor = (1 + (growth_rate / 100)) ** future_years
    
    # 미래 자산 및 수익 계산
    future_total_equity = total_equity * growth_factor
    future_weighted_income = stock_value["weightedIncome"] * growth_factor
    
    # 1. 순자산가치 계산
    net_asset_per_share = future_total_equity / shares
    
    # 2. 영업권 계산
    weighted_income_per_share = future_weighted_income / shares
    weighted_income_per_share_50 = weighted_income_per_share * 0.5
    equity_return = (future_total_equity * (interest_rate / 100)) / shares
    annuity_factor = 3.7908
    goodwill = max(0, (weighted_income_per_share_50 - equity_return) * annuity_factor)
    
    # 3. 순자산가치 + 영업권
    asset_value_with_goodwill = net_asset_per_share + goodwill
    
    # 4. 손익가치 계산
    income_value = weighted_income_per_share * (100 / interest_rate)
    
    # 5. 최종가치 계산
    if evaluation_method == '부동산 과다법인':
        # 부동산 과다법인
        stock_value_calc = (asset_value_with_goodwill * 0.6) + (income_value * 0.4)
        net_asset_80_percent = net_asset_per_share * 0.8
        final_value = max(stock_value_calc, net_asset_80_percent)
        method_text = '부동산 과다법인: (자산가치×0.6 + 수익가치×0.4)'
    elif evaluation_method == '순자산가치만 평가':
        # 순자산가치만 적용
        final_value = net_asset_per_share
        method_text = '순자산가치만 평가'
    else:
        # 일반법인
        stock_value_calc = (income_value * 0.6) + (asset_value_with_goodwill * 0.4)
        net_asset_80_percent = net_asset_per_share * 0.8
        final_value = max(stock_value_calc, net_asset_80_percent)
        method_text = '일반법인: (수익가치×0.6 + 자산가치×0.4)'
    
    # 총 가치
    total_value = final_value * shares
    owned_value = final_value * owned_shares
    
    return {
        "netAssetPerShare": net_asset_per_share,
        "assetValueWithGoodwill": asset_value_with_goodwill,
        "incomeValue": income_value,
        "finalValue": final_value,
        "totalValue": total_value,
        "ownedValue": owned_value,
        "methodText": method_text,
        "futureTotalEquity": future_total_equity,
        "futureWeightedIncome": future_weighted_income,
        "growthRate": growth_rate,
        "futureYears": future_years
    }

# 1. 비상장주식 평가 페이지
if page == "1. 비상장주식 평가":
    st.title("비상장주식 가치평가")
    
    with st.expander("회사 정보", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            company_name = st.text_input("회사명", value="주식회사 에이비씨")
        
        with col2:
            total_equity = st.number_input("자본총계 (원)", 
                                          value=1002804000, 
                                          min_value=0, 
                                          format="%d")
    
    with st.expander("당기순이익 (최근 3개년)", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 1년 전 (가중치 3배)")
            net_income1 = st.number_input("당기순이익 1년 전 (원)", 
                                         value=386650000, 
                                         format="%d")
            
        with col2:
            st.markdown("#### 2년 전 (가중치 2배)")
            net_income2 = st.number_input("당기순이익 2년 전 (원)", 
                                         value=163401000, 
                                         format="%d")
            
        with col3:
            st.markdown("#### 3년 전 (가중치 1배)")
            net_income3 = st.number_input("당기순이익 3년 전 (원)", 
                                         value=75794000, 
                                         format="%d")
    
    with st.expander("주식 정보", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            shares = st.number_input("총 발행주식수", 
                                   value=4000, 
                                   min_value=1, 
                                   format="%d")
            
            owned_shares = st.number_input("대표이사 보유 주식수", 
                                          value=2000, 
                                          min_value=0, 
                                          max_value=shares, 
                                          format="%d")
            
        with col2:
            share_price = st.number_input("액면금액 (원)", 
                                         value=5000, 
                                         min_value=0, 
                                         format="%d")
            
            interest_rate = st.slider("환원율 (%)", 
                                    min_value=1, 
                                    max_value=20, 
                                    value=10, 
                                    help="일반적으로 10% 사용 (시장금리 반영)")
    
    with st.expander("평가 방식 선택", expanded=True):
        evaluation_method = st.selectbox(
            "비상장주식 평가 방법을 선택하세요",
            ("일반법인", "부동산 과다법인", "순자산가치만 평가"),
            help="상속세 및 증여세법 시행령 제54조 근거"
        )
        
        st.info("""
        📌 **평가방식 설명**
        - **일반법인**: 대부분의 법인에 적용 (수익가치 60% + 자산가치 40%)
        - **부동산 과다법인**: 부동산이 자산의 50% 이상인 법인 (자산가치 60% + 수익가치 40%)
        - **순자산가치만 평가**: 특수한 경우 (설립 1년 미만 등) (순자산가치 100%)
        """)
    
    if st.button("비상장주식 평가하기", type="primary", use_container_width=True):
        with st.spinner("계산 중..."):
            st.session_state.stock_value = calculate_stock_value(
                total_equity, net_income1, net_income2, net_income3, 
                shares, interest_rate, evaluation_method, owned_shares
            )
            st.session_state.evaluated = True
            # 세션 상태에 입력 값 저장
            st.session_state.company_name = company_name
            st.session_state.total_equity = total_equity
            st.session_state.shares = shares
            st.session_state.owned_shares = owned_shares
            st.session_state.share_price = share_price
            st.session_state.interest_rate = interest_rate
            st.session_state.evaluation_method = evaluation_method
            
            st.success("계산이 완료되었습니다. '2. 주식가치 결과' 탭에서 결과를 확인하세요.")
            st.balloons()
            # 페이지 자동 전환
            st.experimental_rerun()

# 2. 주식가치 결과 페이지
elif page == "2. 주식가치 결과":
    if not st.session_state.evaluated:
        st.warning("먼저 '1. 비상장주식 평가' 탭에서 평가를 진행해주세요.")
        if st.button("비상장주식 평가 페이지로 이동"):
            st.session_state.page = "1. 비상장주식 평가"
            st.experimental_rerun()
    else:
        stock_value = st.session_state.stock_value
        company_name = st.session_state.company_name
        total_equity = st.session_state.total_equity
        
        st.title("주식가치 평가 결과")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"### 회사명: {company_name}")
        with col2:
            st.markdown(f"### 적용 평가방식: {stock_value['methodText']}")
        
        st.markdown("---")
        
        st.subheader("주요 계산결과")
        
        # 결과 표 생성
        results_df = pd.DataFrame({
            "항목": [
                "1주당 순자산가치", 
                "1주당 손익가치", 
                "영업권 고려 후 자산가치", 
                "최종 주당 평가액", 
                "회사 총 주식가치", 
                "대표이사 보유주식 가치"
            ],
            "금액 (원)": [
                format_number(stock_value["netAssetPerShare"]),
                format_number(stock_value["incomeValue"]),
                format_number(stock_value["assetValueWithGoodwill"]),
                format_number(stock_value["finalValue"]),
                format_number(stock_value["totalValue"]),
                format_number(stock_value["ownedValue"])
            ]
        })
        
        # 하이라이트할 행
        highlight_rows = {3: 'rgba(220, 242, 255, 0.5)', 4: 'rgba(220, 242, 255, 0.5)'}
        
        # 스타일링된 데이터프레임 표시
        st.dataframe(
            results_df,
            column_config={
                "항목": st.column_config.TextColumn("항목"),
                "금액 (원)": st.column_config.TextColumn("금액 (원)", width="large"),
            },
            hide_index=True,
            use_container_width=True,
            height=280
        )
        
        # 증가율 정보 표시
        st.info(f"자본총계({format_number(total_equity)}원) 대비 평가 회사가치는 **{stock_value['increasePercentage']}%**로 평가되었습니다.")
        
        # 차트 표시
        col1, col2 = st.columns(2)
        with col1:
            # 원형 차트 생성
            labels = ['순자산가치', '영업권 가치']
            values = [stock_value["netAssetPerShare"], stock_value["assetValueWithGoodwill"] - stock_value["netAssetPerShare"]]
            
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
            fig.update_layout(title_text='주당 가치 구성')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 막대 차트 생성
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=['순자산가치', '손익가치', '최종평가액'],
                y=[stock_value["netAssetPerShare"], stock_value["incomeValue"], stock_value["finalValue"]],
                marker_color=['lightblue', 'lightgreen', 'coral']
            ))
            fig.update_layout(title_text='주요 가치 비교 (주당)')
            st.plotly_chart(fig, use_container_width=True)
        
        # 버튼 행
        col1, col2 = st.columns(2)
        with col1:
            if st.button("3. 현시점 세금 계산하기", type="primary", use_container_width=True):
                st.session_state.current_tax_details = calculate_tax_details(
                    st.session_state.stock_value,
                    st.session_state.owned_shares,
                    st.session_state.share_price
                )
                st.experimental_rerun()
        
        with col2:
            if st.button("4. 미래 주식가치 계산하기", type="primary", use_container_width=True):
                st.experimental_rerun()

# 3. 현시점 세금계산 페이지
elif page == "3. 현시점 세금계산":
    if not st.session_state.evaluated:
        st.warning("먼저 '1. 비상장주식 평가' 탭에서 평가를 진행해주세요.")
        if st.button("비상장주식 평가 페이지로 이동"):
            st.experimental_rerun()
    else:
        stock_value = st.session_state.stock_value
        company_name = st.session_state.company_name
        owned_shares = st.session_state.owned_shares
        share_price = st.session_state.share_price
        
        # 세금 계산
        current_tax_details = calculate_tax_details(stock_value, owned_shares, share_price)
        
        st.title("현시점 세금 계산")
        
        # 평가된 주식 가치 정보
        with st.expander("평가된 주식 가치", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**회사명:** {company_name}")
                st.markdown(f"**주당 평가액:** {format_number(stock_value['finalValue'])}원")
            with col2:
                st.markdown(f"**회사 총가치:** {format_number(stock_value['totalValue'])}원")
                st.markdown(f"**대표이사 보유주식 가치:** {format_number(stock_value['ownedValue'])}원")
        
        # 세금 계산 결과
        st.subheader("세금 계산 결과")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "증여세", 
                f"{format_number(current_tax_details['inheritanceTax'])}원", 
                "적용 세율: 40%"
            )
        
        with col2:
            st.metric(
                "양도소득세", 
                f"{format_number(current_tax_details['transferTax'])}원", 
                "적용 세율: 22%"
            )
        
        with col3:
            st.metric(
                "청산소득세", 
                f"{format_number(current_tax_details['totalTax'])}원", 
                "법인세 25% + 배당세 15.4%"
            )
        
        # 계산 세부내역
        with st.expander("계산 세부내역", expanded=True):
            details_df = pd.DataFrame({
                "항목": [
                    "증여세 과세표준", 
                    "양도소득 취득가액", 
                    "양도소득 차익", 
                    "법인세 과세표준", 
                    "법인세액", 
                    "배당소득", 
                    "배당소득세"
                ],
                "금액 (원)": [
                    format_number(stock_value["ownedValue"]),
                    format_number(current_tax_details["acquisitionValue"]),
                    format_number(current_tax_details["transferProfit"]),
                    format_number(stock_value["ownedValue"]),
                    format_number(current_tax_details["corporateTax"]),
                    format_number(current_tax_details["afterTaxValue"]),
                    format_number(current_tax_details["liquidationTax"])
                ]
            })
            
            st.dataframe(
                details_df,
                column_config={
                    "항목": st.column_config.TextColumn("항목"),
                    "금액 (원)": st.column_config.TextColumn("금액 (원)", width="large"),
                },
                hide_index=True,
                use_container_width=True
            )
        
        # 참고사항
        st.info("※ 실제 세금은 개인 상황, 보유기간, 대주주 여부 등에 따라 달라질 수 있습니다.")
        
        # 버튼 행
        col1, col2 = st.columns(2)
        with col1:
            if st.button("2. 주식가치 결과로 돌아가기", use_container_width=True):
                st.experimental_rerun()
        
        with col2:
            if st.button("4. 미