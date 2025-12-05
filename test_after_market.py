"""
장 마감 후 API 테스트
- 토큰 재사용
- 주식 현재가 조회
- 일봉 데이터 조회
"""

import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

class AfterMarketTest:
    def __init__(self):
        self.app_key = os.getenv('KIS_APP_KEY')
        self.app_secret = os.getenv('KIS_APP_SECRET')
        self.base_url = "https://openapivts.koreainvestment.com:29443"
        self.kst = pytz.timezone('Asia/Seoul')

        # 토큰 파일에서 읽기
        with open('kis_token.json', 'r') as f:
            token_data = json.load(f)
            self.token = token_data['token']

        print(f"✅ 토큰 로드 성공")
        print(f"🕐 현재 시간: {datetime.now(self.kst).strftime('%Y-%m-%d %H:%M:%S')} KST")
        print("="*60)

    def test_current_price(self, stock_code="005930"):
        """현재가 조회 테스트 (삼성전자)"""
        print(f"\n📊 현재가 조회 테스트: {stock_code}")

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010100"
        }

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") == "0":
                    output = data.get("output", {})
                    print(f"  종목명: {output.get('prdt_name', 'N/A')}")
                    print(f"  현재가: {output.get('stck_prpr', 'N/A')}원")
                    print(f"  전일대비: {output.get('prdy_vrss', 'N/A')}원")
                    print(f"  등락률: {output.get('prdy_ctrt', 'N/A')}%")
                    print(f"  거래량: {output.get('acml_vol', 'N/A')}")
                    print(f"  ✅ 현재가 조회 성공!")
                    return True
                else:
                    print(f"  ❌ API 오류: {data.get('msg1', 'Unknown error')}")
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")
        except Exception as e:
            print(f"  ❌ 예외 발생: {e}")

        return False

    def test_daily_candles(self, stock_code="005930"):
        """일봉 데이터 조회 테스트"""
        print(f"\n📈 일봉 데이터 조회 테스트: {stock_code}")

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST03010100"
        }

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": "20240101",  # 시작일
            "FID_INPUT_DATE_2": datetime.now().strftime("%Y%m%d"),  # 오늘
            "FID_PERIOD_DIV_CODE": "D",  # 일봉
            "FID_ORG_ADJ_PRC": "0"
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") in ["0", ""]:
                    output = data.get("output2", [])  # 일봉은 output2
                    print(f"  일봉 데이터 개수: {len(output)}개")

                    if output and len(output) > 0:
                        latest = output[0]
                        print(f"\n  최근 거래일 데이터:")
                        print(f"  날짜: {latest.get('stck_bsop_date', 'N/A')}")
                        print(f"  시가: {latest.get('stck_oprc', 'N/A')}원")
                        print(f"  고가: {latest.get('stck_hgpr', 'N/A')}원")
                        print(f"  저가: {latest.get('stck_lwpr', 'N/A')}원")
                        print(f"  종가: {latest.get('stck_clpr', 'N/A')}원")
                        print(f"  거래량: {latest.get('acml_vol', 'N/A')}")
                        print(f"  ✅ 일봉 데이터 조회 성공!")
                        return True
                else:
                    print(f"  ❌ API 오류: {data.get('msg1', 'Unknown error')}")
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")
        except Exception as e:
            print(f"  ❌ 예외 발생: {e}")

        return False

    def test_ranking_api(self):
        """등락률 순위 조회 테스트"""
        print(f"\n📊 등락률 순위 조회 테스트")

        url = f"{self.base_url}/uapi/domestic-stock/v1/ranking/fluctuation"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHPST01700000",
            "custtype": "P"
        }

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "20170",
            "FID_INPUT_ISCD": "0000",
            "FID_RANK_SORT_CLS_CODE": "0",
            "FID_INPUT_CNT_1": "0",
            "FID_PAGING_KEY_100": "",
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": "",
            "FID_DIV_CLS_CODE": "0",
            "FID_BLNG_CLS_CODE": "0",
            "FID_TRGT_CLS_CODE": "111111111",
            "FID_TRGT_EXLS_CLS_CODE": "000000",
            "FID_INPUT_DATE_1": ""
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") in ["0", ""]:
                    output = data.get("output", [])
                    print(f"  상승률 상위 종목 수: {len(output)}개")

                    if output and len(output) > 0:
                        print(f"\n  상위 5개 종목:")
                        for i, stock in enumerate(output[:5], 1):
                            code = stock.get('stck_shrn_iscd', 'N/A')
                            name = stock.get('hts_kor_isnm', 'N/A')
                            rate = stock.get('prdy_ctrt', 'N/A')
                            print(f"  {i}. [{code}] {name}: {rate}%")
                        print(f"  ✅ 등락률 순위 조회 성공!")
                        return True
                    else:
                        print(f"  ⚠️ 데이터는 있지만 비어있음 (장 마감)")
                else:
                    print(f"  ❌ API 오류: {data.get('msg1', 'Unknown error')}")
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")
        except Exception as e:
            print(f"  ❌ 예외 발생: {e}")

        return False

    def test_investor_trend(self, stock_code="005930"):
        """투자자별 매매동향 테스트"""
        print(f"\n💰 투자자별 매매동향 테스트: {stock_code}")

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-investor"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010900"
        }

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") == "0":
                    output = data.get("output", {})
                    print(f"  개인 순매수: {output.get('prsn_ntby_qty', 'N/A')}주")
                    print(f"  외국인 순매수: {output.get('frgn_ntby_qty', 'N/A')}주")
                    print(f"  기관 순매수: {output.get('orgn_ntby_qty', 'N/A')}주")
                    print(f"  ✅ 투자자별 매매동향 조회 성공!")
                    return True
                else:
                    print(f"  ❌ API 오류: {data.get('msg1', 'Unknown error')}")
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")
        except Exception as e:
            print(f"  ❌ 예외 발생: {e}")

        return False

def main():
    print("="*60)
    print("🔬 KIS API 장 마감 후 테스트")
    print("="*60)

    tester = AfterMarketTest()

    # 각 테스트 실행
    results = {
        "현재가 조회": tester.test_current_price(),
        "일봉 데이터": tester.test_daily_candles(),
        "등락률 순위": tester.test_ranking_api(),
        "투자자 동향": tester.test_investor_trend()
    }

    # 결과 요약
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)

    for test_name, result in results.items():
        status = "✅ 성공" if result else "❌ 실패"
        print(f"  {test_name}: {status}")

    success_rate = sum(results.values()) / len(results) * 100
    print(f"\n  성공률: {success_rate:.0f}% ({sum(results.values())}/{len(results)})")

    if success_rate == 100:
        print("\n🎉 모든 API가 장 마감 후에도 정상 작동합니다!")
    elif success_rate > 0:
        print("\n⚠️ 일부 API는 장 마감 후에도 작동하지만, 일부는 제한적입니다.")
    else:
        print("\n❌ 장 마감 후 API 사용에 제한이 있습니다.")

if __name__ == "__main__":
    main()