"""振り返りアンケートDBの「閲覧」を「メンバー」と同名のNotionユーザーで埋める。
DRY_RUN=1 でドライラン、DRY_RUN=0 で実行。
"""
import os, sys, json, time, urllib.request, urllib.error

TOKEN = os.environ["NOTION_TOKEN"]
ANKETO_DB = "2fb26386566780ac9fa8e816ce785762"
MEMBERS_DB = "2b979997-a4c4-4a13-ac5c-fa638306f329"
DRY_RUN = os.environ.get("DRY_RUN", "1") == "1"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def req(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:200], file=sys.stderr)
        raise

def get_title(props):
    for k, v in props.items():
        if v.get("type") == "title" and v.get("title"):
            return v["title"][0]["plain_text"]
    return ""

def query_all(db_id):
    cursor = None
    while True:
        body = {"page_size": 100}
        if cursor: body["start_cursor"] = cursor
        d = req("POST", f"https://api.notion.com/v1/databases/{db_id}/query", body)
        for r in d["results"]:
            yield r
        if not d.get("has_more"): break
        cursor = d.get("next_cursor")

def list_users():
    users = []
    cursor = None
    while True:
        url = "https://api.notion.com/v1/users?page_size=100"
        if cursor: url += f"&start_cursor={cursor}"
        d = req("GET", url)
        users.extend(d["results"])
        if not d.get("has_more"): break
        cursor = d.get("next_cursor")
    return users

def norm(s):
    s = (s or "").split("/")[0]
    for ch in [" ", "　", "\t"]:
        s = s.replace(ch, "")
    # 異体字寄せ
    s = s.replace("髙", "高").replace("﨑", "崎").replace("德", "徳")
    return s.strip()

print("Members DB取得中...")
members = {}  # member_page_id -> (name, user_id or None)
for m in query_all(MEMBERS_DB):
    name = get_title(m["properties"])
    ppl = m["properties"].get("ユーザー", {}).get("people", [])
    uid = ppl[0]["id"] if ppl else None
    members[m["id"]] = (name, uid)
print(f"  メンバー: {len(members)}件 / ユーザー紐付け済み: {sum(1 for _,u in members.values() if u)}件")

print("振り返りアンケート走査中...")
targets = []
skipped_no_match = []
total = 0
for r in query_all(ANKETO_DB):
    total += 1
    p = r["properties"]
    mem_rel = p.get("メンバー", {}).get("relation", [])
    view = p.get("閲覧", {}).get("people", [])
    if not mem_rel or view: continue
    mem_id = mem_rel[0]["id"]
    mem_name, user_id = members.get(mem_id, ("", None))
    title = get_title(p)
    if not user_id:
        skipped_no_match.append((title, mem_name))
        continue
    targets.append((r["id"], title, mem_name, user_id))

print(f"\n=== サマリ ===")
print(f"全行: {total}")
print(f"更新対象: {len(targets)}")
print(f"未マッチ(スキップ): {len(skipped_no_match)}")

print(f"\n--- 更新対象 サンプル(先頭10) ---")
for t in targets[:10]:
    print(f"  {t[1]} -> {t[2]}")

print(f"\n--- 未マッチ サンプル(先頭20) ---")
for t in skipped_no_match[:20]:
    print(f"  {t[0]} | member={t[1]}")

if DRY_RUN:
    print("\n[DRY_RUN=1] 実行しない。DRY_RUN=0 で実行。")
    sys.exit(0)

print(f"\n=== 実行開始: {len(targets)}件 ===")
ok = ng = 0
for i, (page_id, title, mem_name, user_id) in enumerate(targets, 1):
    try:
        req("PATCH", f"https://api.notion.com/v1/pages/{page_id}", {
            "properties": {"閲覧": {"people": [{"object": "user", "id": user_id}]}}
        })
        ok += 1
        if i % 20 == 0: print(f"  {i}/{len(targets)} done")
        time.sleep(0.35)
    except Exception as e:
        ng += 1
        print(f"  FAIL {title} ({mem_name}): {e}")
print(f"\n完了: OK={ok}, NG={ng}")
