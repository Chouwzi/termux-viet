# termux-viet — Bộ gõ tiếng Việt cho Termux

Ngày kiểm tra: 2026-10-24. Đây là kết quả khảo sát và đề xuất, chưa phải bản đã triển khai.

Tên dự án và lệnh chính: `termux-viet`. Package Python: `termux_viet`.
Ưu tiên hoàn thiện Telex; kiến trúc cho phép thêm VNI và các kiểu gõ khác.
Tên `tivi` chỉ dùng để chỉ script cũ trong khảo sát và hướng dẫn chuyển đổi.

## Phạm vi và hiện trạng

Bộ gõ đang cài gồm `~/.local/bin/tivi`, `~/.local/bin/vn`,
`~/.local/lib/telexlib.py`, dữ liệu vần và bộ kiểm tra round-trip.
Python đọc bàn phím, chuyển Telex rồi gửi các thao tác xóa/chèn xuống PTY con.
Bash và Zsh có cấu hình tự khởi động tivi; Termux có nút EN/VI riêng.
Các file này chưa nằm trong một repository Git riêng.

## Kết quả tái hiện

| Đầu vào / thao tác | Hiện tại | Kết quả cần có |
| --- | --- | --- |
| `nuwar`, `nuawr` | `nữa` | `nửa` |
| `aaa` | `â` | `aa` |
| `ass` | `á` | `as` |
| `ddd` | `ddd` | `dd` |
| `dd` | `dd` | `đ` ngay khi gõ |
| `khoeo` | `khôe` | `khoeo` |
| Bracketed paste chứa `ass` | Nội dung bị chuyển thành `á` | Giữ nguyên toàn bộ payload |
| Ctrl+Space trong paste | Đổi chế độ | Giữ nguyên byte trong payload |
| Gõ `as`, Ctrl+A, `f` | Gửi xóa/chèn dựa trên từ cũ | Không sửa vùng trước con trỏ mới |
| ESC sequence bị chia giữa các lần đọc | Có thể rơi byte hoặc coi phần đuôi là chữ | Bảo toàn sequence |
| UTF-8 bị chia giữa các lần đọc | Mất đồng bộ trạng thái ghép từ | Bảo toàn ký tự và reset/ghép đúng ranh giới |
| Backspace sau `vieetj` | Gửi lại phần Telex thô | Xóa ký tự hiển thị, cập nhật trạng thái dấu |
| Canonical PTY với VERASE=DEL, gõ `as` + Enter | `a\x08á\n` | `á\n` |

`hoaf` thành `hoà` thay vì `hòa` là lựa chọn kiểu đặt dấu, không tự động
coi là lỗi. Bản mới cần tùy chọn kiểu truyền thống/hiện đại và test riêng.

Bộ corpus hiện có: 2.100 mục, 2.077 khớp chính xác, 23 khác biệt.
Trong đó 17 mục khác kiểu đặt dấu, một mục đổi sai nghĩa `nửa` → `nữa`,
và năm mục lỗi vần `oeo`. Corpus này không chứng minh tính đúng đắn của
PTY, paste hoặc hành vi theo từng phím.

## Nguyên nhân trong source

- `SPELLING_FIXES` ép `nửa` thành `nữa`, làm thay đổi nghĩa văn bản.
- Engine tính lại toàn bộ từ từ phím thô, thiếu trạng thái hủy dấu khi gõ lặp.
- Kiểm tra nguyên âm mũ tìm quá xa về phía trước, phá các vần như `oeo`.
- Bộ kiểm tra âm tiết chỉ chấp nhận từ hoàn chỉnh; chữ đang ghép bị giữ nguyên
  rồi đổi đột ngột. Một số đường xử lý còn tự suy hình dạng chưa được gõ.
- `_erase` luôn gửi BS; không xét VERASE hoặc chế độ canonical của terminal con.
- Backspace bỏ một phím thô thay vì một ký tự đang hiển thị.
- Bộ phân tích input không có trạng thái bracketed paste và bộ đệm UTF-8.
- Không reset ghép từ trên tất cả thao tác đổi vị trí, ví dụ Ctrl+A/Ctrl+E.
- `flush_esc` có thể xóa sequence dở dang mà chưa chuyển tiếp đủ byte.
- Output PTY được decode riêng từng chunk với `replace`, có thể làm hỏng UTF-8.
- Ghi PTY một lần bằng `os.write` không xử lý short write.
- Nhánh chờ kết thúc luôn trả mã 0, không bảo toàn exit status của tiến trình con.
- Debug có thể ghi nội dung phím; không phù hợp khi người dùng nhập dữ liệu riêng tư.
- File mode dùng chung giữa nhiều session và xóa khi một session thoát.
- `vn --last` hỏi history trong shell mới, không lấy được history của shell gọi.

## Nghiên cứu nguồn chính

1. [Hướng dẫn UniKey](https://www.unikey.org/support/ukmanual.html):
   quy tắc Telex, đặt dấu cuối từ, thay dấu, xóa thanh bằng `z`, chữ hoa.
2. [fcitx5-unikey](https://github.com/fcitx/fcitx5-unikey), khảo sát tại commit
   `ed9170c35c1a6275d105e03d7f9bc4f674c1469c`:
   `unikey/inputproc.cpp`, `ukengine.cpp`, `keycons.h`, `unikeyinputcontext.cpp`,
   `test/testunikey.cpp`. Engine đã có xử lý gõ lặp, xóa ký tự và di chuyển dấu.
   Các file lõi có thể build riêng; bỏ lớp tích hợp Fcitx và user keymap phụ thuộc
   Fcitx, không cần cài một desktop input-method framework trên Termux.
3. [TerminalView.java](https://github.com/termux/termux-app/blob/master/terminal-view/src/main/java/com/termux/view/TerminalView.java):
   input connection, commitText và deleteSurroundingText của Android.
4. [TerminalEmulator.java](https://github.com/termux/termux-app/blob/master/terminal-emulator/src/main/java/com/termux/terminal/TerminalEmulator.java):
   paste có marker `ESC[200~`/`ESC[201~` khi DECSET 2004 được bật.
5. [Xterm control sequences](https://www.xfree86.org/current/ctlseqs.html):
   nhóm escape/control strings và chuyển alternate screen.
6. [Funput](https://github.com/Funput/Funput): nguồn mà bản cũ ghi nhận
   dùng để port quy tắc/dữ liệu. Không cần tiếp tục mang dữ liệu này nếu thay
   engine bằng UniKey; giữ đúng attribution nếu tái sử dụng.

## Các hướng triển khai

### A. Tiếp tục engine Python

Không cần compiler khi cài. Tuy nhiên phải tự duy trì toàn bộ quy tắc Telex,
trạng thái gõ từng phím và tương thích UniKey; rủi ro lệch hành vi cao hơn.

### B. UniKey gốc + PTY Python — đề xuất

Lệnh chính `termux-viet`, chuyển văn bản qua `termux-viet convert`.
Đưa lõi UniKey được ghim phiên bản vào `vendor/`,
thêm C ABI nhỏ cho từng instance và gọi bằng `ctypes`. Chỉ cần Python, Git
và Clang khi cài từ source, không cần root hay desktop framework.
Giữ nguyên thông báo tác quyền/license của vendor; source mới dùng GPL-2.0-or-later.
Comment mới chỉ giải thích ràng buộc khó hiểu, không diễn giải lại code.

### C. Sửa Android IME hoặc fork Termux

Tích hợp được composition ở cấp ứng dụng nhưng tăng rất nhiều phạm vi build,
cài APK và bảo trì. Không phù hợp mục tiêu hoàn thiện bộ gõ đang cài.

## Thiết kế đề xuất cho hướng B

- `src/termux_viet/engine.py`: API ghép phím/backspace/reset và các chỉnh sửa đầu ra.
- `native/`: C ABI sở hữu engine riêng cho từng instance, đầu ra UTF-8,
  biên dịch thư viện nhỏ; không để exception C++ đi qua ABI.
- `src/termux_viet/input.py`: parser byte có trạng thái; xử lý UTF-8 và escape phân mảnh,
  paste giữ nguyên byte, giới hạn bộ đệm, không phụ thuộc kích thước chunk.
- `src/termux_viet/terminal.py`: PTY, write đầy đủ, resize, raw byte output,
  khôi phục terminal và truyền exit status/signal của child.
- `src/termux_viet/cli.py`: chế độ VI/EN, tùy chọn kiểu dấu, chuyển văn bản và diagnostics
  không ghi nội dung gõ.
- `scripts/`: cài/gỡ, backup, cấu hình shell và Termux có thể chạy lặp an toàn.
- `tests/`: regression từng phím, fixture độc lập, parser mọi điểm chia chunk,
  kiểm thử PTY thật, installer trong HOME tạm và smoke test Bash/Zsh.
- `docs/`: nghiên cứu, kiến trúc, hướng dẫn phát triển và giới hạn tương thích.

Giữ Ctrl+Space, Alt+Space và nút EN/VI; không nuốt mọi Alt+chữ hoa.
EN phải truyền nguyên dữ liệu ngoài các phím chuyển chế độ được công bố.
Paste có marker phải được giữ nguyên cả khi chứa control bytes.
Khi di chuyển con trỏ, reset vùng ghép; không tự sửa từ cũ nếu không biết
nội dung xung quanh. Tự tạm dừng chuyển dấu ở trường nhập mật khẩu canonical
không echo và alternate screen; cung cấp EN thủ công cho ứng dụng raw đặc thù.
Không thể hứa tương đương Android IME trong mọi TUI chỉ bằng một PTY wrapper.

Mặc định không tự suy dấu chưa gõ và không sửa nghĩa từ. VNI chưa cung cấp
trong giao diện bản đầu. Chuỗi đã có dấu/emoji đi qua nguyên vẹn theo ranh giới
được kiểm thử; không chạy thêm một bộ ghép Telex thứ hai trên chữ Android IME đã commit.

## GitFlow và phát hành đề xuất

Repo mới dự kiến `Chouwzi/termux-viet`, public, chỉ chứa file dự án được chọn rõ ràng.
Không lấy toàn bộ HOME, cấu hình cá nhân, shell history, SSH key, token hay log.
Không công bố địa chỉ email cá nhân từ cấu hình máy; dùng địa chỉ noreply cho commit.

Luồng Git: `main` → `develop` → `feature/unikey-pty` → `develop` →
`release/0.1.0` → `main`, tag `v0.1.0`, merge release trở lại `develop`.
Ghi commit theo từng thay đổi có thể review; không force push.
Thêm CI Linux cho build/test và hướng dẫn xác minh trên Termux.
Kiểm tra cả danh sách file và nội dung toàn bộ lịch sử trước lần push public đầu.

## Điều kiện nghiệm thu

1. Regression có đầu ra mong đợi độc lập, bao gồm lỗi đã tái hiện ở trên.
2. Thao tác engine có kết quả nhất quán khi gõ sớm/cuối từ, đổi/xóa/lặp dấu,
   hoa/thường, `qu`/`gi`, `ươ`, Backspace và restart vùng ghép.
3. Parser cho cùng kết quả tại mọi điểm chia chunk của UTF-8/escape/paste.
4. PTY canonical và Bash/Zsh nhận đúng Unicode; giữ nguyên dữ liệu output,
   mã thoát, resize và cấu hình terminal sau thoát/lỗi.
5. Cài/gỡ/cài lại trong HOME tạm, kiểm tra backup và không nhân đôi shell hooks.
6. Kiểm thử trực tiếp trên Termux hiện tại và ghi rõ thiết bị/app chưa xác minh.
7. README có lệnh cài, bật/tắt, rollback, troubleshooting và giới hạn đã biết.
8. Chỉ sau khi kiểm tra license, secret, tests và release mới publish GitHub.

## Trạng thái

Đã hoàn thành khảo sát source hiện tại, tái hiện lỗi engine/parser/PTY,
đối chiếu tài liệu và đọc source upstream. Chưa thay bộ gõ đang dùng,
chưa tạo repo GitHub và chưa tuyên bố đã sửa lỗi.
