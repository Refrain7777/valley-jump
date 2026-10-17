# 山谷跳跃

网页版无限跑酷跳跃游戏（电脑浏览器 / 手机横屏均可）。

在线玩：**https://refrain7777.github.io/valley-jump/**

请用系统浏览器打开（Chrome、Safari、Edge、手机自带浏览器）。微信里点开经常打不开或一直停在加载，请用右上角菜单选择「在浏览器中打开」。

第一次打开会下载大约 **22MB** 的游戏引擎和 pygame（压缩后实际传输大约 **10MB**）。页面上会显示中文进度、百分比和已下载大小。下完之后浏览器会缓存，再次打开会快很多。

- 电脑：WASD 移动，空格或 W 跳跃，J 攻击，B 商店
- 手机：左下方向，右下「跳 / 攻」，右上「商店」，请横屏

## 合并后怎么确认 Pages 正常

推到 `main` 之后，等 Actions 里的 “Deploy game to GitHub Pages” 成功，再检查：

1. 用系统浏览器打开上面的地址，并强制刷新一次。
2. 应看到「山谷跳跃」加载画面，文字是中文，并出现百分比或「x MB / y MB」。不应只剩英文 “Loading, please wait...”。
3. 开发者工具的网络面板里，不应再请求 `pygame-web.github.io`，也不应再出现 `browserfs.min.js` 的 404。体积大的 `main.wasm`、`main.data` 和 pygame 轮子来自本站 `vendor/`。
4. 进度结束后进入开始界面，点「开始游戏」能正常跑。

本地试玩仍用 `pack_web.bat`（同样是中文加载画面，引擎由 pygbag 在本机代理）。GitHub Pages 会在 `pygbag --build` 之后运行 `scripts/vendor_pages.py`，把引擎文件放进 `build/web/vendor` 再发布。
