"""
銘柄リサーチDBの全銘柄に対してyfinanceで最新指標を取得するスクリプト。

使い方:
  python fetch_indicators.py '[{"code":"6701","name":"NEC"},{"code":"9432","name":"NTT"}]'

出力: JSON形式で各銘柄の指標を返す
"""

import sys
import json

def install_yfinance():
    """yfinanceをインストールする。失敗時はフォールバックを試す。"""
    import subprocess
    try:
        import yfinance
        return True
    except ImportError:
        pass
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "yfinance",
            "--break-system-packages", "-q"
        ])
        return True
    except subprocess.CalledProcessError:
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "yfinance",
                "--break-system-packages", "--only-binary=:all:", "-q"
            ])
            return True
        except subprocess.CalledProcessError:
            return False


def calc_equity_ratio(ticker):
    """balance_sheetから自己資本比率を計算する。"""
    try:
        bs = ticker.balance_sheet
        if bs.empty:
            return None
        equity = bs.loc["Stockholders Equity"].iloc[0]
        total_assets = bs.loc["Total Assets"].iloc[0]
        if total_assets and total_assets != 0:
            return round(float(equity / total_assets), 4)
    except Exception:
        pass
    return None


def calc_roe(ticker):
    """balance_sheet + financialsからROEを計算する。"""
    try:
        bs = ticker.balance_sheet
        fi = ticker.financials
        if bs.empty or fi.empty:
            return None
        equity = bs.loc["Stockholders Equity"].iloc[0]
        net_income = fi.loc["Net Income"].iloc[0]
        if equity and equity != 0:
            return round(float(net_income / equity), 4)
    except Exception:
        pass
    return None


def sanitize_per(trailing_pe, forward_pe):
    """PERの異常値を検知し、有効な値を返す。"""
    def is_valid(v):
        return v is not None and 0.01 <= v <= 500

    if is_valid(trailing_pe):
        return round(trailing_pe, 2), "trailing"
    elif is_valid(forward_pe):
        return round(forward_pe, 2), "forward"
    else:
        return None, "unavailable"


def fetch_one(code, name):
    """1銘柄の指標を取得する。"""
    import yfinance as yf

    ticker_code = f"{code}.T"
    result = {
        "code": code,
        "name": name,
        "status": "ok",
        "current_price": None,
        "per": None,
        "per_source": None,
        "pbr": None,
        "roe": None,
        "equity_ratio": None,
        "market_cap": None,
    }

    try:
        t = yf.Ticker(ticker_code)
        info = t.info

        # ティッカーが見つからない場合
        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            result["status"] = "not_found"
            return result

        # 基本指標
        result["current_price"] = info.get("currentPrice") or info.get("regularMarketPrice")
        result["pbr"] = round(info["priceToBook"], 2) if info.get("priceToBook") else None
        result["market_cap"] = info.get("marketCap")

        # PER（異常値検知付き）
        per, per_source = sanitize_per(info.get("trailingPE"), info.get("forwardPE"))
        result["per"] = per
        result["per_source"] = per_source

        # ROE（infoから取れなければ計算）
        roe_raw = info.get("returnOnEquity")
        if roe_raw is not None:
            result["roe"] = round(roe_raw * 100, 2)  # パーセント表記
        else:
            roe_calc = calc_roe(t)
            if roe_calc is not None:
                result["roe"] = round(roe_calc * 100, 2)

        # 自己資本比率（balance_sheetから計算）
        equity_ratio = calc_equity_ratio(t)
        if equity_ratio is not None:
            result["equity_ratio"] = round(equity_ratio * 100, 2)  # パーセント表記

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "銘柄リストをJSON引数で渡してください"}))
        sys.exit(1)

    # yfinanceインストール
    if not install_yfinance():
        print(json.dumps({"error": "yfinanceのインストールに失敗しました"}))
        sys.exit(1)

    stocks = json.loads(sys.argv[1])
    results = []

    for stock in stocks:
        code = stock["code"]
        name = stock["name"]
        result = fetch_one(code, name)
        results.append(result)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()