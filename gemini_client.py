"""
Gemini Web Client - Tương tác với Gemini qua giao diện web
Thay thế cho Gemini API khi bị giới hạn quota
"""

import os
import time
import random
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from browser_manager import BrowserManager


class GeminiWebClient:
    """
    Client tương tác với Gemini qua giao diện web, vượt qua giới hạn API.
    Sử dụng Playwright với profile đã đăng nhập sẵn.
    """
    
    def __init__(self, headless: bool = True, profile_dir: str = "Profile 230"):
        self.headless = headless
        self.profile_dir = profile_dir
        self.playwright = None
        self.browser = BrowserManager("account_1", "E:\\ToolAir\\tiktok_human_chrome\\chrome-profile-debug", profile_dir, proxy=None)
        self.page = None
        self._is_ready = False
        
    def start(self):
        """Khởi tạo trình duyệt và mở Gemini"""
        if self._is_ready:
            return
        
        print("🚀 Đang khởi động Gemini Web Client...")
        _, _, self.page = self.browser.launch()
        
        # Nếu chưa có profile, tạo mới và yêu cầu đăng nhập
        # if not os.path.exists(self.profile_dir):
        #     self._create_profile_and_login()
        
        # self.browser = self.playwright.chromium.launch_persistent_context(
        #     user_data_dir=self.profile_dir,
        #     headless=self.headless,
        #     viewport={"width": 1280, "height": 720}
        # )
        
        # self.page = self.browser.new_page()
        # self.page.goto("https://gemini.google.com/", timeout=30000)
        # time.sleep(60)
        
        # Kiểm tra đăng nhập
        if not self._is_logged_in():
            print("⚠️ Phiên đăng nhập đã hết hạn! Vui lòng đăng nhập lại.")
            self._re_login()
        
        self._is_ready = True
        print("✅ Gemini Web Client sẵn sàng")
    
    def _create_profile_and_login(self):
        """Tạo profile mới và hướng dẫn đăng nhập"""
        print("📝 Chưa có profile Gemini. Vui lòng đăng nhập thủ công...")
        
        temp_browser = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.profile_dir,
            headless=False
        )
        temp_page = temp_browser.new_page()
        temp_page.goto("https://gemini.google.com/")
        
        input("✅ Sau khi đăng nhập thành công, nhấn Enter để tiếp tục...")
        
        temp_browser.close()
        print("✅ Profile đã được lưu")
    
    def _is_logged_in(self) -> bool:
        """Kiểm tra xem đã đăng nhập chưa"""
        try:
            if self.page.locator("text=Sign in").count() > 0:
                return False
            if self.page.locator("[aria-label='Account']").count() > 0:
                return True
            if "gemini.google.com" in self.page.url and "accounts.google.com" not in self.page.url:
                return True
            return False
        except:
            return False
    
    def _re_login(self):
        """Yêu cầu đăng nhập lại khi session hết hạn"""
        self.page.goto("https://gemini.google.com/")
        input("🔐 Vui lòng đăng nhập lại Gemini, sau đó nhấn Enter...")
        time.sleep(2)
    
    def _wait_for_response(self, timeout: int = 90) -> str:
        """Chờ Gemini trả lời và lấy nội dung phản hồi"""
        # Chờ loading indicator biến mất
        loading_selectors = [
            ".loading-indicator",
            "[role='progressbar']",
            ".animate-pulse",
            ".loading",
            "[data-loading='true']"
        ]
        
        for selector in loading_selectors:
            try:
                self.page.wait_for_selector(selector, state="detached", timeout=5000)
            except PlaywrightTimeoutError:
                pass
        
        # Chờ thêm 2-5 giây để response hoàn tất
        time.sleep(random.uniform(2, 4))
        
        # Lấy nội dung phản hồi
        response_selectors = [
            ".message-content:last-child",
            ".markdown:last-child",
            ".prose:last-child",
            "[data-message-content]:last-child",
            ".model-response:last-child"
        ]
        
        for selector in response_selectors:
            try:
                elements = self.page.locator(selector).all()
                if elements:
                    text = elements[-1].inner_text()
                    if text and len(text) > 10:
                        return text
            except:
                continue
        
        # Fallback: lấy toàn bộ nội dung chat
        try:
            chat_container = self.page.locator(".conversation-container, [role='log'], .chat-history")
            if chat_container.count() > 0:
                all_text = chat_container.first.inner_text()
                messages = [m.strip() for m in all_text.split("\n\n") if m.strip()]
                if messages:
                    return messages[-1]
        except:
            pass
        
        raise Exception("Không thể lấy phản hồi từ Gemini")
    
    def _find_input_box(self):
        """Tìm ô input trong giao diện Gemini"""
        input_selectors = [
            "div[contenteditable='true']",
            "textarea",
            "rich-textarea",
            ".ql-editor",
            "[role='textbox']",
            ".input-area",
            "div[contenteditable='true'][aria-label*='message']"
        ]
        
        for selector in input_selectors:
            try:
                if self.page.locator(selector).count() > 0:
                    return self.page.locator(selector).first
            except:
                continue
        
        raise Exception("Không tìm thấy ô input")
    
    def ask(self, prompt: str, max_retries: int = 3) -> str:
        """Gửi câu hỏi đến Gemini và nhận phản hồi"""
        if not self._is_ready:
            self.start()
        
        for attempt in range(max_retries):
            try:
                input_box = self._find_input_box()
                input_box.click()
                time.sleep(random.uniform(0.3, 0.7))
                
                input_box.fill("")
                time.sleep(random.uniform(0.2, 0.5))
                
                input_box.fill(prompt)
                time.sleep(random.uniform(0.5, 1))
                
                self.page.keyboard.press("Enter")
                response = self._wait_for_response()
                
                if prompt in response:
                    response = response.split(prompt)[-1].strip()
                
                time.sleep(random.uniform(2, 4))
                return response
                
            except Exception as e:
                print(f"  ⚠️ Lần thử {attempt+1} thất bại: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    try:
                        self.page.reload()
                        time.sleep(3)
                    except:
                        pass
        
        raise Exception(f"Không thể nhận phản hồi từ Gemini sau {max_retries} lần thử")
    
    def translate(self, text: str, target_lang: str = "vi") -> str:
        """Dịch văn bản từ tiếng Trung sang tiếng Việt"""
        prompt = f"""Dịch đoạn văn sau từ tiếng Trung sang tiếng Việt. Yêu cầu:
- Giữ nguyên phong cách quảng cáo, tự nhiên, hấp dẫn
- Nếu đoạn văn có giọng nói của người review, hãy thể hiện sự hào hứng
- Chỉ trả về nội dung đã dịch, không thêm giải thích

Đoạn văn:
{text}"""
        
        response = self.ask(prompt)
        
        # Làm sạch response
        lines = response.strip().split('\n')
        if lines and any(word in lines[0].lower() for word in ['dịch', 'đoạn', 'văn', 'bản']):
            response = '\n'.join(lines[1:]) if len(lines) > 1 else response
        
        return response.strip()
    
    def generate_caption(self, product_name: str) -> tuple:
        """Tạo caption và hashtag cho TikTok"""
        prompt = f"""Tạo nội dung cho video TikTok về sản phẩm '{product_name}'. Yêu cầu:
- Caption ngắn gọn, thu hút, kích thích tương tác (tối đa 100 ký tự)
- 3-5 hashtag phổ biến, liên quan đến sản phẩm và thị trường Việt Nam
- Format trả về: CAPTION: [nội dung caption] | HASHTAGS: #tag1 #tag2 #tag3

Chỉ trả về đúng format trên, không thêm bất kỳ nội dung nào khác."""
        
        response = self.ask(prompt)
        
        caption = ""
        hashtags = ""
        
        if "CAPTION:" in response and "HASHTAGS:" in response:
            try:
                caption_part = response.split("| HASHTAGS:")[0]
                caption = caption_part.replace("CAPTION:", "").strip()
                hashtags = response.split("| HASHTAGS:")[1].strip()
            except:
                caption = response[:100]
                hashtags = f"#{product_name.replace(' ', '').lower()}"
        else:
            caption = response[:100]
            hashtags = f"#{product_name.replace(' ', '').lower()}"
        
        return caption, hashtags
    
    def close(self):
        """Đóng trình duyệt và giải phóng tài nguyên"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self._is_ready = False
        print("👋 Đã đóng Gemini Web Client")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()