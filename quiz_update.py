import os
import base64
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# ================= CONFIG =================
WP_URL = "https://blog.mexc.com/wp-json/wp/v2/posts"
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)
POST_ID = 304794

TARGET_H2_TEXT = "Xenea Wallet Daily Quiz Today for December 16, 2025"
CHECK_ANSWER = "A) Smart-contract Layer 1..."

# ngày find & replace
OLD_DATE = "December 16"
NEW_DATE = "December 17"


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
    url = "https://www.quiknotes.in/xenea-wallet-daily-quiz-answer-17-december-2025/"
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

    # 1. Fetch current post
    url = f"{WP_URL}/{POST_ID}"
    response = requests.get(url, headers=headers, timeout=15)
    print("🔎 Fetch status:", response.status_code)
    if response.status_code != 200:
        print("❌ Không lấy được post:", response.text[:300])
        return False

    post = response.json()
    if "content" not in post or "rendered" not in post["content"]:
        print("❌ Không thấy content.rendered:", post)
        return False

    old_content = post["content"]["rendered"]
    print("✍️ Lấy content.rendered, độ dài:", len(old_content))

    # 2. Parse HTML
    soup = BeautifulSoup(old_content, "html.parser")

    # 3. Tìm <h2>
    h2_tag = soup.find("h2", string=lambda t: t and target_h2_text in t)
    if not h2_tag:
        print("❌ Không tìm thấy H2 phù hợp")
        print("Rendered snippet:", old_content[:400])
        return False

    # 4. Identify the <p> blocks after H2
    next_tag = h2_tag.find_next_sibling()

    description_p = None
    question_p = None
    answer_p = None

    # Find first 3 <p> tags
    p_tags = []
    while next_tag and len(p_tags) < 3:
        if next_tag.name == "p":
            p_tags.append(next_tag)
        next_tag = next_tag.find_next_sibling()

    if len(p_tags) < 3:
        print("❌ Không tìm đủ 3 <p> sau H2 theo format mới.")
        return False

    description_p, question_p, answer_p = p_tags

    # =======================
    # Update QUESTION <p>
    # =======================
    # Giữ nguyên phần <strong>The question for DATE:</strong>
    strong_tag = question_p.find("strong")
    if strong_tag:
        prefix = strong_tag.get_text(strip=True) + " "
        question_p.string = ""  # Clear old text
        question_p.append(strong_tag)
        question_p.append(" " + question)

    # =======================
    # Update ANSWER <p>
    # =======================
    strong_ans = answer_p.find("strong")
    answer_p.string = ""
    if strong_ans:
        answer_p.append(strong_ans)
        answer_p.append(" " + answer)

    # ===== UPDATE CRYPTO SNAPSHOT (ALWAYS RUN) =====
    update_crypto_price_snapshot(soup)
    
    # ========== FIND & REPLACE DATE TRONG CONTENT ==========
    new_content = str(soup)
    new_content = new_content.replace(OLD_DATE, NEW_DATE)

    # ========== UPDATE POST (content only) ==========
    payload = {
        "content": new_content,
        "status": "publish"
    }

    update = requests.post(url, headers=headers, json=payload, timeout=15)
    print("🚀 Update content status:", update.status_code)

    if update.status_code != 200:
        print("❌ Error khi update content")
        return False

    print("✅ Content updated thành công!")

    # ============================
    # UPDATE WP POST TITLE
    # ============================
    
    updated_post = update.json()
    current_title = updated_post.get("title", {}).get("rendered", "")
    
    new_title = current_title.replace(OLD_DATE, NEW_DATE)
    
    title_payload = {
        "title": new_title
    }
    
    title_update = requests.post(url, headers=headers, json=title_payload, timeout=15)
    print("📝 Update Title status:", title_update.status_code)
    
    if title_update.status_code == 200:
        print("✅ WP Post Title updated")
    else:
        print("⚠️ Title update failed (Content was updated OK)")

    return True


# ================ REWRITE SNAPSHOT ================

def rewrite_crypto_snapshot_with_openai(old_text):
    prompt = f"""
You are a crypto market analyst writing a daily market snapshot.

Rewrite the following crypto price snapshot with:
- Updated prices (use approximate realistic current values)
- Natural, non-duplicated wording
- Professional, neutral tone
- Similar length
- DO NOT mention dates
- DO NOT add promotional language

IMPORTANT:
- Keep references to BTC, ETH, and SOL
- Do NOT include URLs
- Return 3 paragraphs ONLY, separated by newline.

TEXT:
{old_text}
"""

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content.strip()

def update_crypto_price_snapshot(soup):
    h2 = soup.find(
        "h2",
        string=lambda t: t and "Crypto Price Watch: BTC, ETH, and Altcoins" in t
    )

    if not h2:
        print("⚠️ Không tìm thấy Crypto Price Watch H2")
        return False

    # Collect <p> until next H2
    p_tags = []
    cur = h2.find_next_sibling()
    while cur and cur.name != "h2":
        if cur.name == "p":
            p_tags.append(cur)
        cur = cur.find_next_sibling()

    if len(p_tags) < 4:
        print("⚠️ Không đủ paragraph cho Crypto Price Snapshot")
        return False

    intro_p = p_tags[0]          # giữ nguyên
    snapshot_ps = p_tags[1:4]    # chỉ update 3 đoạn này

    # Extract plain text (anchors removed for AI)
    plain_text = "\n\n".join(
    p.get_text(" ", strip=True) for p in snapshot_ps
)

    print("🤖 Sending snapshot to OpenAI...")
    new_text = rewrite_crypto_snapshot_with_openai(plain_text)
    new_paragraphs = new_text.split("\n")

    if len(new_paragraphs) != 3:
        print("⚠️ OpenAI trả về sai format")
        return False

    # Inject new text back but KEEP <a> tags
    for i, p in enumerate(snapshot_ps):
        anchors = p.find_all("a")
        p.clear()
        p.append(new_paragraphs[i])

        # Re-attach anchors at original positions (safe approach)
        for a in anchors:
            p.append(" ")
            p.append(a)

    print("✅ Crypto snapshot updated")
    return True

# ================ MAIN =================
if __name__ == "__main__":
    q1, a1 = scrape_quiz_site1()

    if a1.strip() != CHECK_ANSWER.strip():
        print("✅ Site1 answer khác CHECK_ANSWER -> Update ngay")
        success = update_post_after_h2(TARGET_H2_TEXT, q1, a1)
        if success:
            print("🎉 All updates (Q/A + date + SEO) completed!")
    else:
        print("⚠️ Site1 answer trùng CHECK_ANSWER -> Thử site2")
        try:
            q2, a2 = scrape_quiz_site2()
            if a2.strip() != CHECK_ANSWER.strip():
                print("✅ Site2 answer khác CHECK_ANSWER -> Update")
                success = update_post_after_h2(TARGET_H2_TEXT, q2, a2)
                if success:
                    print("🎉 All updates completed!")
            else:
                print("⚠️ Site2 answer trùng CHECK_ANSWER -> Không update")
        except Exception as e:
            print("❌ Lỗi khi scrape site2:", e)
