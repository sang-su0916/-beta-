import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import base64
from io import BytesIO

# 페이지 설정
st.set_page_config(
    page_title="기업가치 약식 평가계산기",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 사용자 정의 CSS 스타일 적용
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stApp {
        background-color: #f8f9fa;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f3f5;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4e8df5 !important;
        color: white !important;
    }
    .highlight-box {
        background-color: #e8f4f8;
        padding: 20px;
        border-radius: 5px;
        border-left: 5px solid #4e8df5;
        margin-bottom: 20px;
    }
    .card {
        padding: 20px;
        border-radius: 5px;
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 사이드바 설정
with st.sidebar:
    st.title("기업가치 약식 평가계산기")
    st.markdown("---")
    st.markdown("## 비상장주식 평가 및 세금계산기")
    st.markdown("상속세 및 증여세법에 따른 비상장주식 가치평가와 세금 계산을 도와드립니다.")
    st.markdown("---")
    
    pages = ["1. 비상장주식 평가", "2. 주식가치 결과", "3. 현시점 세금계산", "4. 미래 주식가치", "5. 미래 세금계산"]
    page = st.radio("페이지 선택", pages)
    
    st.markdown("---")
    st.info("이 앱은 참고용으로만 사용하세요. 정확한 평가는 전문가와 상담하세요.")

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
    if num is None:
        return "0"
    return f"{int(num):,}"

# 엑셀 다운로드 함수
def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.close()
    processed_data = output.getvalue()
    return processed_data

def get_table_download_link(df, filename, text):
    """Generates a link allowing the data in a given dataframe to be downloaded as Excel"""
    val = to_excel(df)
    b64 = base64.b64encode(val)
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}.xlsx">{text}</a>'

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
    transfer_tax = transfer_profit * 0.22 if transfer_profit > 0 else 0
    
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
        
        st.markdown("""
        <div class="highlight-box">
        <h4>📌 평가방식 설명</h4>
        <ul>
            <li><strong>일반법인</strong>: 대부분의 법인에 적용 (수익가치 60% + 자산가치 40%)</li>
            <li><strong>부동산 과다법인</strong>: 부동산이 자산의 50% 이상인 법인 (자산가치 60% + 수익가치 40%)</li>
            <li><strong>순자산가치만 평가</strong>: 특수한 경우 (설립 1년 미만 등) (순자산가치 100%)</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # 데이터 불러오기/저장 기능
    with st.expander("데이터 저장 및 불러오기", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 현재 데이터 저장")
            if st.button("현재 입력값 JSON으로 다운로드"):
                input_data = {
                    "company_name": company_name,
                    "total_equity": total_equity,
                    "net_income1": net_income1,
                    "net_income2": net_income2,
                    "net_income3": net_income3,
                    "shares": shares,
                    "owned_shares": owned_shares,
                    "share_price": share_price,
                    "interest_rate": interest_rate,
                    "evaluation_method": evaluation_method
                }
                
                # 데이터프레임으로 변환하여 다운로드 링크 생성
                df = pd.DataFrame([input_data])
                st.markdown(get_table_download_link(df, f"{company_name}_평가데이터", "📥 다운로드하기"), unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 저장된 데이터 불러오기")
            uploaded_file = st.file_uploader("Excel 파일을 업로드하세요 (.xlsx)", type=["xlsx"])
            if uploaded_file is not None:
                try:
                    df = pd.read_excel(uploaded_file)
                    st.success("파일을 성공적으로 불러왔습니다!")
                    
                    if st.button("불러온 데이터로 설정"):
                        # 데이터를 입력 필드에 설정
                        st.session_state.company_name = df.iloc[0]['company_name']
                        st.session_state.total_equity = df.iloc[0]['total_equity']
                        st.session_state.net_income1 = df.iloc[0]['net_income1']
                        st.session_state.net_income2 = df.iloc[0]['net_income2']
                        st.session_state.net_income3 = df.iloc[0]['net_income3']
                        st.session_state.shares = df.iloc[0]['shares']
                        st.session_state.owned_shares = df.iloc[0]['owned_shares']
                        st.session_state.share_price = df.iloc[0]['share_price']
                        st.session_state.interest_rate = df.iloc[0]['interest_rate']
                        st.session_state.evaluation_method = df.iloc[0]['evaluation_method']
                        st.experimental_rerun()
                except Exception as e:
                    st.error(f"파일 로드 오류: {str(e)}")
    
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
            # 페이지 자동 전환을 위한 쿼리 파라미터 설정
            st.experimental_set_query_params(page="2")
            st.experimental_rerun()

# 2. 주식가치 결과 페이지
elif page == "2. 주식가치 결과":
    if not st.session_state.evaluated:
        st.warning("먼저 '1. 비상장주식 평가' 탭에서 평가를 진행해주세요.")
        if st.button("비상장주식 평가 페이지로 이동"):
            st.experimental_set_query_params(page="1")
            st.experimental_rerun()
    else:
        stock_value = st.session_state.stock_value
        company_name = st.session_state.company_name
        total_equity = st.session_state.total_equity
        
        st.title("주식가치 평가 결과")
        
        st.markdown(f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between;">
                <div>
                    <h3>회사명: {company_name}</h3>
                </div>
                <div>
                    <h3>적용 평가방식: {stock_value['methodText']}</h3>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
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
            fig.update_layout(
                title_text='주당 가치 구성',
                title_font_size=16,
                height=400,
                margin=dict(l=10, r=10, t=50, b=10),
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 막대 차트 생성
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=['순자산가치', '손익가치', '최종평가액'],
                y=[stock_value["netAssetPerShare"], stock_value["incomeValue"], stock_value["finalValue"]],
                marker_color=['lightblue', 'lightgreen', 'coral'],
                text=[format_number(stock_value["netAssetPerShare"]), 
                      format_number(stock_value["incomeValue"]), 
                      format_number(stock_value["finalValue"])],
                textposition='auto'
            ))
            fig.update_layout(
                title_text='주요 가치 비교 (주당)',
                title_font_size=16,
                height=400,
                margin=dict(l=10, r=10, t=50, b=10),
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # 결과 다운로드 기능
        st.markdown("### 결과 다운로드")
        col1, col2 = st.columns(2)
        with col1:
            # 결과 데이터프레임을 생성하여 다운로드 링크 제공
            full_results_df = pd.DataFrame([{
                "회사명": company_name,
                "평가방법": stock_value['methodText'],
                "자본총계": total_equity,
                "순자산가치(주당)": stock_value["netAssetPerShare"],
                "손익가치(주당)": stock_value["incomeValue"],
                "영업권고려후자산가치(주당)": stock_value["assetValueWithGoodwill"],
                "최종평가액(주당)": stock_value["finalValue"],
                "회사총가치": stock_value["totalValue"],
                "보유주식가치": stock_value["ownedValue"],
                "증가율(%)": stock_value["increasePercentage"],
                "계산일자": datetime.now().strftime("%Y-%m-%d")
            }])
            
            st.markdown(get_table_download_link(full_results_df, f"{company_name}_평가결과", "📊 평가결과 다운로드"), unsafe_allow_html=True)
        
        # 버튼 행
        st.markdown("### 다음 단계")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("3. 현시점 세금 계산하기", type="primary", use_container_width=True):
                st.session_state.current_tax_details = calculate_tax_details(
                    st.session_state.stock_value,
                    st.session_state.owned_shares,
                    st.session_state.share_price
                )
                st.experimental_set_query_params(page="3")
                st.experimental_rerun()
        
        with col2:
            if st.button("4. 미래 주식가치 계산하기", type="primary", use_container_width=True):
                st.experimental_set_query_params(page="4")
                st.experimental_rerun()

# 3. 현시점 세금계산 페이지
elif page == "3. 현시점 세금계산":
    if not st.session_state.evaluated:
        st.warning("먼저 '1. 비상장주식 평가' 탭에서 평가를 진행해주세요.")
        if st.button("비상장주식 평가 페이지로 이동"):
            st.experimental_set_query_params(page="1")
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
            
            # 세부 결과 다운로드 기능
            st.markdown(get_table_download_link(details_df, f"{company_name}_세금계산_결과", "💰 세금계산 결과 다운로드"), unsafe_allow_html=True)
        
        # 시각화
        col1, col2 = st.columns(2)
        with col1:
            # 세금 비교 차트
            tax_fig = go.Figure()
            tax_fig.add_trace(go.Bar(
                x=['증여세', '양도소득세', '청산소득세'],
                y=[current_tax_details['inheritanceTax'], 
                   current_tax_details['transferTax'], 
                   current_tax_details['totalTax']],
                marker_color=['#FF9999', '#66B2FF', '#99CC99'],
                text=[format_number(current_tax_details['inheritanceTax']), 
                      format_number(current_tax_details['transferTax']), 
                      format_number(current_tax_details['totalTax'])],
                textposition='auto'
            ))
            tax_fig.update_layout(
                title='세금 유형별 비교',
                height=400,
                margin=dict(l=10, r=10, t=50, b=10)
            )
            st.plotly_chart(tax_fig, use_container_width=True)
        
        with col2:
            # 청산소득세 구성 파이 차트
            labels = ['법인세', '배당소득세']
            values = [current_tax_details['corporateTax'], current_tax_details['liquidationTax']]
            
            pie_fig = go.Figure(data=[go.Pie(
                labels=labels, 
                values=values, 
                hole=.3,
                marker_colors=['#5D9CEC', '#FC6E51']
            )])
            pie_fig.update_layout(
                title='청산소득세 구성',
                height=400,
                margin=dict(l=10, r=10, t=50, b=10)
            )
            st.plotly_chart(pie_fig, use_container_width=True)
        
        # 참고사항
        st.info("※ 실제 세금은 개인 상황, 보유기간, 대주주 여부 등에 따라 달라질 수 있습니다.")
        st.warning("※ 본 계산기는 참고용이며, 정확한 세금 계산은 세무사와 상담하시기 바랍니다.")
        
        # 버튼 행
        col1, col2 = st.columns(2)
        with col1:
            if st.button("2. 주식가치 결과로 돌아가기", use_container_width=True):
                st.experimental_set_query_params(page="2")
                st.experimental_rerun()
        
        with col2:
            if st.button("4. 미래 주식가치 계산하기", type="primary", use_container_width=True):
                st.experimental_set_query_params(page="4")
                st.experimental_rerun()

# 4. 미래 주식가치 페이지
elif page == "4. 미래 주식가치":
    if not st.session_state.evaluated:
        st.warning("먼저 '1. 비상장주식 평가' 탭에서 평가를 진행해주세요.")
        if st.button("비상장주식 평가 페이지로 이동"):
            st.experimental_set_query_params(page="1")
            st.experimental_rerun()
    else:
        st.title("미래 주식가치 예측")
        
        with st.expander("현재 평가 정보", expanded=True):
            stock_value = st.session_state.stock_value
            company_name = st.session_state.company_name
            total_equity = st.session_state.total_equity
            shares = st.session_state.shares
            owned_shares = st.session_state.owned_shares
            interest_rate = st.session_state.interest_rate
            evaluation_method = st.session_state.evaluation_method
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**회사명:** {company_name}")
                st.markdown(f"**현재 주당 평가액:** {format_number(stock_value['finalValue'])}원")
                st.markdown(f"**현재 회사 총가치:** {format_number(stock_value['totalValue'])}원")
            with col2:
                st.markdown(f"**현재 자본총계:** {format_number(total_equity)}원")
                st.markdown(f"**총 발행주식수:** {format_number(shares)}주")
                st.markdown(f"**대표이사 보유 주식수:** {format_number(owned_shares)}주")
        
        # 성장률 및 기간 설정
        st.subheader("미래 성장 가정")
        col1, col2 = st.columns(2)
        
        with col1:
            growth_rate = st.slider(
                "연간 성장률 (%)", 
                min_value=0, 
                max_value=30, 
                value=10,
                help="회사의 연간 예상 성장률을 설정하세요"
            )
        
        with col2:
            future_years = st.slider(
                "예측 기간 (년)", 
                min_value=1, 
                max_value=20, 
                value=5,
                help="몇 년 후의 가치를 예측할지 설정하세요"
            )
        
        # 미래 가치 계산 버튼
        if st.button("미래 주식가치 계산하기", type="primary", use_container_width=True):
            with st.spinner("미래 가치 계산 중..."):
                st.session_state.future_stock_value = calculate_future_stock_value(
                    stock_value, total_equity, shares, owned_shares,
                    interest_rate, evaluation_method, growth_rate, future_years
                )
                st.session_state.future_evaluated = True
                st.session_state.growth_rate = growth_rate
                st.session_state.future_years = future_years
                
                st.success(f"{future_years}년 후의 주식가치 계산이 완료되었습니다!")
        
        # 미래 가치 결과 표시
        if st.session_state.future_evaluated and st.session_state.future_stock_value:
            future_value = st.session_state.future_stock_value
            
            st.markdown("---")
            st.subheader(f"{future_years}년 후 주식가치 결과")
            
            # 현재값과 미래값 비교 테이블
            comparison_df = pd.DataFrame({
                "항목": [
                    "자본총계", 
                    "가중평균 당기순이익", 
                    "1주당 순자산가치", 
                    "1주당 손익가치", 
                    "1주당 최종 평가액", 
                    "회사 총 주식가치", 
                    "대표이사 보유주식 가치"
                ],
                "현재 (원)": [
                    format_number(total_equity),
                    format_number(stock_value["weightedIncome"]),
                    format_number(stock_value["netAssetPerShare"]),
                    format_number(stock_value["incomeValue"]),
                    format_number(stock_value["finalValue"]),
                    format_number(stock_value["totalValue"]),
                    format_number(stock_value["ownedValue"])
                ],
                f"{future_years}년 후 (원)": [
                    format_number(future_value["futureTotalEquity"]),
                    format_number(future_value["futureWeightedIncome"]),
                    format_number(future_value["netAssetPerShare"]),
                    format_number(future_value["incomeValue"]),
                    format_number(future_value["finalValue"]),
                    format_number(future_value["totalValue"]),
                    format_number(future_value["ownedValue"])
                ],
                "증가율 (%)": [
                    f"{((future_value['futureTotalEquity']/total_equity) - 1) * 100:.1f}%",
                    f"{((future_value['futureWeightedIncome']/stock_value['weightedIncome']) - 1) * 100:.1f}%",
                    f"{((future_value['netAssetPerShare']/stock_value['netAssetPerShare']) - 1) * 100:.1f}%",
                    f"{((future_value['incomeValue']/stock_value['incomeValue']) - 1) * 100:.1f}%",
                    f"{((future_value['finalValue']/stock_value['finalValue']) - 1) * 100:.1f}%",
                    f"{((future_value['totalValue']/stock_value['totalValue']) - 1) * 100:.1f}%",
                    f"{((future_value['ownedValue']/stock_value['ownedValue']) - 1) * 100:.1f}%"
                ]
            })
            
            st.dataframe(
                comparison_df,
                column_config={
                    "항목": st.column_config.TextColumn("항목"),
                    "현재 (원)": st.column_config.TextColumn("현재 (원)"),
                    f"{future_years}년 후 (원)": st.column_config.TextColumn(f"{future_years}년 후 (원)"),
                    "증가율 (%)": st.column_config.TextColumn("증가율 (%)")
                },
                hide_index=True,
                use_container_width=True
            )
            
            # 다운로드 기능
            st.markdown(get_table_download_link(comparison_df, f"{company_name}_{future_years}년후_예측", "📊 미래가치 예측 결과 다운로드"), unsafe_allow_html=True)
            
            # 가치 변화 시각화
            st.subheader("가치 변화 시각화")
            
            col1, col2 = st.columns(2)
            with col1:
                # 주당 가치 비교 차트
                fig1 = go.Figure()
                fig1.add_trace(go.Bar(
                    x=['현재', f'{future_years}년 후'],
                    y=[stock_value["finalValue"], future_value["finalValue"]],
                    text=[format_number(stock_value["finalValue"]), format_number(future_value["finalValue"])],
                    textposition='auto',
                    marker_color=['#5D9CEC', '#FC6E51']
                ))
                fig1.update_layout(
                    title='주당 가치 변화',
                    height=400,
                    margin=dict(l=20, r=20, t=50, b=20)
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # 총 회사 가치 비교 차트
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    x=['현재', f'{future_years}년 후'],
                    y=[stock_value["totalValue"], future_value["totalValue"]],
                    text=[format_number(stock_value["totalValue"]), format_number(future_value["totalValue"])],
                    textposition='auto',
                    marker_color=['#5D9CEC', '#FC6E51']
                ))
                fig2.update_layout(
                    title='회사 총 가치 변화',
                    height=400,
                    margin=dict(l=20, r=20, t=50, b=20)
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # 미래 성장 시뮬레이션
            st.subheader("다양한 성장률에 따른 미래 가치 시뮬레이션")
            
            # 다양한 성장률에 대한 시뮬레이션 계산
            growth_rates = [5, 10, 15, 20, 25]
            simulation_years = list(range(1, future_years + 1))
            
            # 시뮬레이션 데이터 생성
            sim_data = []
            for gr in growth_rates:
                values = []
                for yr in simulation_years:
                    future_val = calculate_future_stock_value(
                        stock_value, total_equity, shares, owned_shares,
                        interest_rate, evaluation_method, gr, yr
                    )
                    values.append(future_val["finalValue"])
                sim_data.append((gr, values))
            
            # 라인 차트로 시각화
            fig3 = go.Figure()
            for gr, values in sim_data:
                fig3.add_trace(go.Scatter(
                    x=simulation_years,
                    y=values,
                    mode='lines+markers',
                    name=f'성장률 {gr}%',
                    hovertemplate='%{y:,.0f}원'
                ))
            
            fig3.update_layout(
                title='성장률별 주당 가치 예측',
                xaxis_title='예측 기간 (년)',
                yaxis_title='주당 가치 (원)',
                height=500,
                hovermode='x unified'
            )
            st.plotly_chart(fig3, use_container_width=True)
            
            # 버튼 행
            col1, col2 = st.columns(2)
            with col1:
                if st.button("2. 주식가치 결과로 돌아가기", use_container_width=True):
                    st.experimental_set_query_params(page="2")
                    st.experimental_rerun()
            
            with col2:
                if st.button("5. 미래 세금 계산하기", type="primary", use_container_width=True):
                    st.experimental_set_query_params(page="5")
                    st.experimental_rerun()

# 5. 미래 세금계산 페이지
elif page == "5. 미래 세금계산":
    if not st.session_state.future_evaluated:
        st.warning("먼저 '4. 미래 주식가치' 탭에서 미래 가치 평가를 진행해주세요.")
        if st.button("미래 주식가치 페이지로 이동"):
            st.experimental_set_query_params(page="4")
            st.experimental_rerun()
    else:
        future_value = st.session_state.future_stock_value
        company_name = st.session_state.company_name
        owned_shares = st.session_state.owned_shares
        share_price = st.session_state.share_price
        future_years = st.session_state.future_years
        growth_rate = st.session_state.growth_rate
        
        # 현재 및 미래 세금 계산
        current_tax_details = calculate_tax_details(
            st.session_state.stock_value,
            owned_shares,
            share_price
        )
        
        future_tax_details = calculate_tax_details(
            future_value,
            owned_shares,
            share_price
        )
        
        st.title(f"{future_years}년 후 세금 계산")
        
        with st.expander(f"{future_years}년 후 주식 가치", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**회사명:** {company_name}")
                st.markdown(f"**예측 기간:** {future_years}년")
            with col2:
                st.markdown(f"**연간 성장률:** {growth_rate}%")
                st.markdown(f"**주당 평가액:** {format_number(future_value['finalValue'])}원")
            with col3:
                st.markdown(f"**회사 총가치:** {format_number(future_value['totalValue'])}원")
                st.markdown(f"**대표이사 보유주식 가치:** {format_number(future_value['ownedValue'])}원")
        
        # 세금 비교 결과
        st.subheader("현재 vs 미래 세금 비교")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            inheritance_change = ((future_tax_details['inheritanceTax'] / current_tax_details['inheritanceTax']) - 1) * 100
            st.metric(
                "증여세", 
                f"{format_number(future_tax_details['inheritanceTax'])}원", 
                f"{inheritance_change:.1f}% 증가"
            )
        
        with col2:
            transfer_change = ((future_tax_details['transferTax'] / max(current_tax_details['transferTax'], 1)) - 1) * 100
            st.metric(
                "양도소득세", 
                f"{format_number(future_tax_details['transferTax'])}원", 
                f"{transfer_change:.1f}% 증가"
            )
        
        with col3:
            liquidation_change = ((future_tax_details['totalTax'] / current_tax_details['totalTax']) - 1) * 100
            st.metric(
                "청산소득세", 
                f"{format_number(future_tax_details['totalTax'])}원", 
                f"{liquidation_change:.1f}% 증가"
            )
        
        # 세금 비교 테이블
        tax_comparison_df = pd.DataFrame({
            "세금 유형": [
                "증여세 (40%)", 
                "양도소득세 (22%)", 
                "청산소득세 (법인세+배당세)"
            ],
            "현재 (원)": [
                format_number(current_tax_details["inheritanceTax"]),
                format_number(current_tax_details["transferTax"]),
                format_number(current_tax_details["totalTax"])
            ],
            f"{future_years}년 후 (원)": [
                format_number(future_tax_details["inheritanceTax"]),
                format_number(future_tax_details["transferTax"]),
                format_number(future_tax_details["totalTax"])
            ],
            "증가액 (원)": [
                format_number(future_tax_details["inheritanceTax"] - current_tax_details["inheritanceTax"]),
                format_number(future_tax_details["transferTax"] - current_tax_details["transferTax"]),
                format_number(future_tax_details["totalTax"] - current_tax_details["totalTax"])
            ]
        })
        
        st.dataframe(
            tax_comparison_df,
            column_config={
                "세금 유형": st.column_config.TextColumn("세금 유형"),
                "현재 (원)": st.column_config.TextColumn("현재 (원)"),
                f"{future_years}년 후 (원)": st.column_config.TextColumn(f"{future_years}년 후 (원)"),
                "증가액 (원)": st.column_config.TextColumn("증가액 (원)")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # 다운로드 기능
        st.markdown(get_table_download_link(tax_comparison_df, f"{company_name}_{future_years}년후_세금비교", "💰 세금 비교 데이터 다운로드"), unsafe_allow_html=True)
        
        # 세금 비교 시각화
        st.subheader("세금 비교 시각화")
        
        # 세금 비교 차트
        fig = go.Figure()
        
        tax_types = ["증여세", "양도소득세", "청산소득세"]
        current_taxes = [current_tax_details["inheritanceTax"], 
                        current_tax_details["transferTax"], 
                        current_tax_details["totalTax"]]
        future_taxes = [future_tax_details["inheritanceTax"], 
                       future_tax_details["transferTax"], 
                       future_tax_details["totalTax"]]
        
        fig.add_trace(go.Bar(
            name='현재',
            x=tax_types,
            y=current_taxes,
            text=[format_number(tax) for tax in current_taxes],
            textposition='auto',
            marker_color='#5D9CEC'
        ))
        
        fig.add_trace(go.Bar(
            name=f'{future_years}년 후',
            x=tax_types,
            y=future_taxes,
            text=[format_number(tax) for tax in future_taxes],
            textposition='auto',
            marker_color='#FC6E51'
        ))
        
        fig.update_layout(
            title='세금 유형별 현재-미래 비교',
            barmode='group',
            height=500,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 세금 절감 전략
        with st.expander("세금 절감 전략 (참고용)", expanded=True):
            st.markdown("""
            <div class='highlight-box'>
            <h4>💡 세금 절감 전략 참고 정보</h4>
            <ul>
                <li><strong>증여세 전략:</strong> 10년에 걸쳐 나누어 증여하는 방식으로 누진세율 효과를 줄일 수 있습니다.</li>
                <li><strong>가업상속공제:</strong> 가업승계 시 요건을 충족하면 최대 500억원까지 상속세 공제 가능합니다.</li>
                <li><strong>사전증여:</strong> 사망 전 10년 이내 증여재산은 상속세 과세대상이나, 증여세와 상속세 중 유리한 세액 적용됩니다.</li>
                <li><strong>양도소득세 이월과세:</strong> 적격 합병·분할 시 양도차익에 대한 과세이연 가능합니다.</li>
                <li><strong>사업전환 투자세액공제:</strong> 신사업 진출 시 투자금액의 일정비율을 세액공제 받을 수 있습니다.</li>
            </ul>
            <p>※ 위 내용은 참고용이며, 세부 상황에 맞게 세무사와 상담하시기 바랍니다.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # 참고사항
        st.info("※ 실제 세금은 개인 상황, 보유기간, 세법 개정 등에 따라 달라질 수 있습니다.")
        st.warning("※ 본 계산기는 참고용이며, 정확한 세금 계산은 세무사와 상담하시기 바랍니다.")
        
        # 버튼 행
        col1, col2 = st.columns(2)
        with col1:
            if st.button("4. 미래 주식가치로 돌아가기", use_container_width=True):
                st.experimental_set_query_params(page="4")
                st.experimental_rerun()
        
        with col2:
            if st.button("1. 처음으로 돌아가기", type="primary", use_container_width=True):
                # 세션 상태 초기화
                for key in ['evaluated', 'future_evaluated', 'stock_value', 'future_stock_value']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.experimental_set_query_params(page="1")
                st.experimental_rerun()

# 맨 아래 푸터 정보
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888;">
    <p>© 2025 기업가치 약식 평가계산기 | 상속세 및 증여세법에 기반한 참고용 계산 도구</p>
    <p style="font-size: 0.8em;">이 앱은 교육 및 참고 목적으로만 사용되어야 하며, 실제 의사결정에는 전문가와 상담하세요.</p>
</div>
""", unsafe_allow_html=True)

# GitHub 코드 링크 (실제 레포지토리 URL로 변경 필요)
st.sidebar.markdown("---")
st.sidebar.markdown("[GitHub 코드 보기](https://github.com/yourusername/business-valuation-calculator)")
st.sidebar.markdown("[버그 신고 및 제안](https://github.com/yourusername/business-valuation-calculator/issues)")
