import base64
import requests
from bs4 import BeautifulSoup

# ================= CONFIG =================
WP_URL = "https://blog.mexc.com/wp-json/wp/v2/posts"
WP_USERNAME = "AI Picks"   # ⚠️ username login thật (không phải Display Name)
WP_APP_PASSWORD = "BZjF 3sMe HQgG 041j y079 SaFQ"  # giữ nguyên format
POST_ID = 300359  # ID bài muốn update
TARGET_H2_TEXT = "Xenea Wallet Daily Quiz Today’s Answer – November 2, 2025"
CHECK_ANSWER = "D. Replicates to a new DACS node."

# ================ SCRAPE SITE 1 ================
def scrape_quiz_site1():
    url = "https://miningcombo.com/xenea-wallet/"
    print(f"[+] Scraping quiz from {url}")
    r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    ps = soup.find_all("p", class_="has-text-align-left", limit=2)
    if len(ps) < 2:
        raise RuntimeError("Không tìm thấy 2 thẻ p class has-text-align-left")
    question = ps[0].get_text(strip=True).replace("Quiz:", "").strip()
    answer = ps[1].get_text(strip=True).replace("Answer:", "").strip()
    print("[+] Scraped question and answer (site1)")
    print("   Q:", question)
    print("   A:", answer)
    return question, answer

# ================ SCRAPE SITE 2 ================
def scrape_quiz_site2():
    url = "https://www.quiknotes.in/xenea-wallet-daily-quiz-answer-2-november-2025/"
    print(f"[+] Scraping quiz from {url}")
    r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    ul = soup.find("ul", class_="wp-block-list")
    if not ul:
        raise RuntimeError("Không tìm thấy <ul class='wp-block-list'>")
    lis = ul.find_all("li")
    if len(lis) < 2:
        raise RuntimeError("Không tìm thấy đủ <li> trong danh sách")
    question = lis[0].get_text(strip=True).replace("Quiz:", "").strip()
    answer = lis[1].get_text(strip=True).replace("Answer:", "").strip()
    print("[+] Scraped question and answer (site2)")
    print("   Q:", question)
    print("   A:", answer)
    return question, answer

# ================ UPDATE POST ================
def update_post_after_h2(target_h2_text, question, answer):
    token = base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode("utf-8")
    headers = {
        "Authorization": f"Basic {token}",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    # 1. Fetch current post (rendered content)
    url = f"{WP_URL}/{POST_ID}"
    response = requests.get(url, headers=headers, timeout=15)
    print("🔎 Fetch status:", response.status_code)
    if response.status_code != 200:
        print("❌ Không lấy được post:", response.text[:300])
        return

    post = response.json()
    if "content" not in post or "rendered" not in post["content"]:
        print("❌ Không thấy content.rendered:", post)
        return

    old_content = post["content"]["rendered"]
    print("✍️ Lấy content.rendered, độ dài:", len(old_content))

    # 2. Parse HTML
    soup = BeautifulSoup(old_content, "html.parser")

    # 3. Tìm <h2> có text khớp
    h2_tag = soup.find("h2", string=lambda t: t and target_h2_text in t)
    if not h2_tag:
        print("❌ Không tìm thấy H2 phù hợp")
        print("Rendered snippet:", old_content[:400])
        return

    # 4. Xóa 2 <p> liền kề sau H2 (nếu có)
    next_tag = h2_tag.find_next_sibling()
    removed = 0
    for _ in range(2):
        if next_tag and next_tag.name == "p":
            to_remove = next_tag
            next_tag = next_tag.find_next_sibling()
            to_remove.decompose()
            removed += 1
    print(f"[+] Removed {removed} <p> sau H2")

    # 5. Tạo Q/A mới
    q_tag = soup.new_tag("p")
    q_tag.string = f"Question: {question}"

    a_tag = soup.new_tag("p")
    a_tag.append("Answer: ")

    strong = soup.new_tag("strong")
    strong.string = answer
    a_tag.append(strong)

    # 6. Chèn Q/A sau H2
    h2_tag.insert_after(a_tag)
    h2_tag.insert_after(q_tag)

    new_content = str(soup)
    print("[+] New content length:", len(new_content))

    # 7. Update & publish
    payload = {
        "content": new_content,
        "status": "publish"
    }
    update = requests.post(url, headers=headers, json=payload, timeout=15)
    print("🚀 Update status:", update.status_code)
    print("📄 Update response:", update.text[:500])

    if update.status_code == 200:
        print("✅ Post updated & published thành công!")
    else:
        print("❌ Error khi update")

# ================ MAIN =================
if __name__ == "__main__":
    q1, a1 = scrape_quiz_site1()

    if a1.strip() != CHECK_ANSWER.strip():
        print("✅ Site1 answer khác CHECK_ANSWER -> Update ngay")
        update_post_after_h2(TARGET_H2_TEXT, q1, a1)
    else:
        print("⚠️ Site1 answer trùng CHECK_ANSWER -> Thử site2")
        try:
            q2, a2 = scrape_quiz_site2()
            if a2.strip() != CHECK_ANSWER.strip():
                print("✅ Site2 answer khác CHECK_ANSWER -> Update")
                update_post_after_h2(TARGET_H2_TEXT, q2, a2)
            else:
                print("⚠️ Site2 answer cũng trùng CHECK_ANSWER -> Không update")
        except Exception as e:
            print("❌ Lỗi khi scrape site2:", e)
