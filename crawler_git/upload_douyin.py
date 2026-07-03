import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page.get_by_role("button", name="上传视频").click()
    page.get_by_role("button", name="上传视频").set_input_files("YouTube短视频测试")
    page.goto("https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page")
    page.get_by_role("textbox", name="填写作品标题，为作品获得更多流量").click()
    page.get_by_role("textbox", name="填写作品标题，为作品获得更多流量").fill("YouTube短视频测试")
    page.locator(".zone-container").click()
    page.locator(".zone-container").fill("#YouTube短视频测试 ​")
    page.locator(".mask-ivBFbc").first.click()
    page.get_by_role("button", name="确定").click()
    page.locator(".semi-icons").first.click()
    page.locator("div:nth-child(6) > .outer-acaJ0e > .outer-img-wrap-ItpQQ9 > img").click()
    page.locator("canvas").nth(5).click(position={"x":360,"y":238})
    page.locator("canvas").nth(5).click(position={"x":166,"y":197})
    page.locator("canvas").nth(5).dblclick(position={"x":247,"y":288})
    page.get_by_role("textbox", name="输入封面文字，最多40字").click()
    page.get_by_role("textbox", name="输入封面文字，最多40字").fill("YouTube短视频测试")
    page.get_by_role("button", name="确定").click()
    page.get_by_role("button", name="完成").click()
    page.locator("label").filter(has_text="仅自己可见").click()
    page.get_by_role("button", name="发布", exact=True).click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
