# termux-viet

Bộ gõ tiếng Việt gọn nhẹ cho terminal Termux, dùng **lõi UniKey**.
Gõ Telex trực tiếp vào terminal, đổi Việt/Anh ngay trên bàn phím.
Không cần root, desktop framework hay thư viện Python ngoài.

**Bản 0.2.0:** Telex. VNI và các kiểu gõ khác dành cho phiên bản sau.
Đây là bộ chuyển phím trong terminal; không có dự đoán từ hoặc autocorrect
như Gboard/Samsung Keyboard.

## Cài đặt

Trong Termux:

```sh
pkg install python clang git
git clone https://github.com/Chouwzi/termux-viet.git
cd termux-viet
sh install.sh
export PATH="$HOME/.local/bin:$PATH"
termux-viet doctor
termux-viet
```

Cần Python 3.10+ và compiler C++17. Build diễn ra trên thiết bị nên dùng được
trên các kiến trúc Termux khác mà không tải binary không rõ nguồn.
Sau khi clone, build/cài/chạy không cần mạng. Không dùng `pip install` cho bản này.

Muốn tự bật khi mở Bash/Zsh, thêm nút đổi EN/VI trước ESC và chuyển từ script cũ:

```sh
sh install.sh --auto-start --termux-keys --migrate
termux-reload-settings
```

Mở session mới để áp dụng shell hook. Các tùy chọn độc lập:

| Tùy chọn | Tác dụng |
| --- | --- |
| `--auto-start` | Thêm hook có đánh dấu vào `.bashrc` và `.zshrc`, thêm thư mục lệnh vào PATH |
| `--termux-keys` | Thêm một nút đổi EN/VI trước ESC, giữ phím mặc định/tùy chỉnh |
| `--migrate` | Gỡ đúng block tự chạy `tivi` cũ đã nhận diện; giữ các script cũ |
| `--prefix PATH` | Cài vào prefix khác, mặc định `~/.local` |

File cấu hình thay đổi được sao lưu tại `~/.local/state/termux-viet/backups/`
(hoặc dưới `XDG_STATE_HOME`). Đường dẫn backup được in khi cài.
Cài lại cập nhật bản chạy và không nhân đôi hook. Không sửa cấu hình bàn phím
Android hay các file dữ liệu cá nhân khác.

## Sử dụng

```sh
termux-viet                         # shell với Telex, bắt đầu VI
termux-viet --en                    # bắt đầu EN
termux-viet -- bash --noprofile --norc
termux-viet --modern                # hoà, thuỷ thay cho hòa, thủy
termux-viet --no-spell-check        # cho phép cấu trúc âm tiết không chuẩn
termux-viet convert 'tieengs Vieetj'
printf '%s\n' 'nuwar nuwax' | termux-viet convert
```

| Phím | Chức năng |
| --- | --- |
| Ctrl+Space, Alt+Space, Alt+`\` | Đổi VI/EN |
| Nút EN / VI trước ESC | Chuyển sang chế độ được ghi trên nút |
| `s f r x j` | Sắc, huyền, hỏi, ngã, nặng |
| `aa ee oo`, `aw ow uw`, `dd` | â ê ô, ă ơ ư, đ |
| `w` | Gõ nhanh ư theo UniKey |
| `z` | Xóa dấu thanh |
| Lặp phím dấu | Hủy dấu và nhập phím literal: `ass` → `as`, `aaa` → `aa` |

Gõ dấu ngay sau nguyên âm hoặc cuối từ: `nuwar`/`nuawr` → `nửa`,
`tieengs` → `tiếng`, `dduowcj` → `được`. Không tự đổi `nửa` thành `nữa`
và không bổ sung dấu chưa gõ. Backspace xóa ký tự hiển thị.

### Nút đổi ngôn ngữ

Sau khi cài với `--termux-keys`, nút đổi ngôn ngữ nằm ngay trước ESC.
Tất cả phím mặc định, gồm ←/→, được giữ lại. Khi nâng từ bố cục cũ của
termux-viet, vị trí EN/VI thay nhầm ←/→ được sửa lại.

Nhãn là **chế độ sẽ chuyển sang**: đang VI thì nút ghi **EN**; đang EN thì nút
ghi **VI**. Bấm nút gửi Ctrl+Space để đổi đúng chế độ của session đang nhập.
Đổi bằng phím tắt cũng cập nhật nhãn ở nền, không chèn thông báo vào dòng gõ.

Cập nhật bản đang cài và bố cục:

```sh
git pull --ff-only
sh install.sh --auto-start --termux-keys
termux-reload-settings
```

Mở session mới để chạy phiên bản mới. Termux dùng **một cấu hình hàng phím
chung cho toàn ứng dụng**: nhãn phản ánh session cập nhật gần nhất, có thể cũ
khi chuyển giữa các session có chế độ khác nhau. Bấm nút vẫn luôn đổi chế độ
thực tế của session hiện tại. Không có polling khi chờ gõ; reload chỉ chạy
khi nhãn thay đổi. Đặt `TERMUX_VIET_MODE_KEY=0` để tắt cập nhật nhãn tự động.

Dùng layout **English** của Gboard/Samsung Keyboard khi bật VI trong termux-viet,
tránh hai bộ gõ cùng chuyển dấu. Chuyển **EN khi gõ lệnh shell, code, URL hoặc
chuỗi tiếng Anh cần giữ nguyên**; Telex có các phím chữ kiêm dấu nên không thể
phân biệt mọi từ Việt/Anh theo ý người gõ.

Chế độ từng session có tại `$TERMUX_VIET_MODE_FILE` nếu muốn tích hợp prompt.
Không in thông báo đổi chế độ giữa dòng đang nhập và không ghi log phím gõ.
`exit` hoặc Ctrl+D trong shell con kết thúc session bộ gõ.

## Paste, editor và giới hạn

- Paste có bracketed markers đi qua nguyên payload; marker được giữ hoặc gỡ
  tùy chương trình con có yêu cầu chúng hay không. Không dùng tốc độ gõ để đoán paste.
- UTF-8/escape phân mảnh được giữ nguyên; output chương trình không bị decode rồi encode lại.
- Phím di chuyển, history, Tab và control keys kết thúc vùng ghép hiện tại.
  Sau khi quay lại một từ cũ, không tự phục dựng từ quanh con trỏ.
- Tự tạm dừng Telex trong alternate screen và vùng nhập mật khẩu canonical không echo.
  Vim/tmux hoặc ứng dụng toàn màn hình có thể cần chuyển EN; bộ gõ không biết
  chế độ Insert/Normal của editor nằm bên trong một terminal khác.
- Mật khẩu dùng raw mode, ứng dụng tự vẽ form và một số TUI không thể phân biệt
  chắc chắn bằng PTY; chọn EN trước khi nhập chuỗi cần giữ nguyên.
- Các shortcut dấu ngoặc `[`/`]` của UniKey không được bật, để giữ nguyên cú pháp shell.
- Tính năng prediction, sửa chính tả từ vựng và composition cấp Android IME
  nằm ngoài phạm vi bản này. Không tuyên bố tương đương mọi hành vi của bàn phím thương mại.

## Tắt tự chạy, gỡ và khôi phục

Tắt tự chạy nhưng giữ chương trình:

```sh
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/termux-viet"
touch "${XDG_CONFIG_HOME:-$HOME/.config}/termux-viet/off"
```

Xóa file `off` để bật lại. Gỡ:

```sh
termux-viet uninstall
termux-reload-settings
```

Lệnh gỡ bỏ chương trình/hook được quản lý, giữ backup và cấu hình riêng.
Hàng extra keys cũ được phục hồi nếu bố cục hiện tại chưa được bạn sửa thêm.
Nếu đã tùy chỉnh, chỉ nút của termux-viet được gỡ. Các chỉnh sửa khác của bạn
trong `termux.properties` được giữ nguyên.
Để quay lại cấu hình trước khi chuyển đổi, chép file tương ứng từ đường dẫn
backup đã in về `.bashrc`, `.zshrc` hoặc `.termux/termux.properties`, rồi mở session mới.

## Phát triển và kiểm chứng

```sh
python scripts/build.py
PYTHONPATH=src python -m unittest discover -v
PYTHONPATH=src python scripts/benchmark.py
```

Kiểm thử gồm 1.307 cặp mẫu Telex upstream, regression riêng, parser phân mảnh,
PTY thật, backpressure/SIGTERM, mã thoát, resize, Bash/Zsh và cài/gỡ trong HOME tạm.
CI Linux không thay thế kiểm tra giao diện bàn phím Android trên từng thiết bị.

Đo trên Termux aarch64, Python 3.14.6, Clang 21.1.8: native library 158.648 byte,
engine trung vị khoảng 5,5 µs/phím, parser khoảng 176.000 phím/giây; RSS của
tiến trình benchmark khoảng 18 MiB. Đây là benchmark engine/parser trên một máy,
không phải độ trễ end-to-end của Gboard hay cam kết cho mọi thiết bị.
Relay chờ sự kiện khi idle và dùng hàng đợi ghi không chặn có giới hạn.

Xem [kiến trúc](docs/architecture.md), [nghiên cứu](docs/research.md),
[đóng góp và GitFlow](CONTRIBUTING.md), [changelog](CHANGELOG.md).

## License

GPL-2.0-or-later. Lõi UniKey từ [fcitx5-unikey](https://github.com/fcitx/fcitx5-unikey)
được ghim commit và giữ nguyên thông báo tác quyền/license từng file.
Xem [vendor/README.md](vendor/README.md), [LICENSE](LICENSE) và `LICENSES/`.
