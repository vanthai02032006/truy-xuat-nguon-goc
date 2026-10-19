# Báo cáo Spike: Bảo vệ bản ghi sự kiện chuỗi cung ứng

## 1. Mục tiêu

So sánh ba phương án bảo vệ bản ghi sự kiện chuỗi cung ứng:

1. Sử dụng chuỗi hash tự viết trong bảng thông thường.
2. Sử dụng quyền PostgreSQL để giới hạn thao tác dữ liệu.
3. Sử dụng PostgreSQL Trigger để từ chối cập nhật và xóa bản ghi.

Mục tiêu là đánh giá cách hoạt động, khả năng phát hiện hoặc ngăn sửa dữ liệu, độ phức tạp, ưu điểm và hạn chế của từng phương án.

Các thử nghiệm được thực hiện trong phạm vi spike trên những đối tượng kiểm thử riêng biệt.

## 2. Phương án 1: Sử dụng chuỗi hash tự viết

### 2.1. Mục tiêu

Phát hiện việc thay đổi nội dung bản ghi bằng cách tính hash cho từng sự kiện và liên kết mỗi bản ghi với hash của bản ghi trước đó.

### 2.2. Cách thực hiện

Tạo bảng `public.events_hash_test` trong cơ sở dữ liệu `spike_security_test`. Bảng gồm các trường:

- `event_id`: mã sự kiện.
- `event_type`: loại sự kiện.
- `event_data`: nội dung sự kiện.
- `previous_hash`: hash của bản ghi trước.
- `current_hash`: hash của bản ghi hiện tại.

Sử dụng thuật toán SHA-256 thông qua hàm `digest()` của PostgreSQL và chuyển kết quả sang chuỗi hex bằng hàm `encode()`.

Khi kiểm tra, hệ thống tính lại hash từ nội dung bản ghi rồi so sánh với giá trị `current_hash` đã lưu. Đồng thời, cần kiểm tra `previous_hash` của mỗi bản ghi có khớp với `current_hash` của bản ghi trước hay không.
n ghi có hash hợp lệ riêng lẻ vẫn có thể liên kết sai với bản ghi trước.
- Nếu người có đủ quyền sửa dữ liệu và tính lại hash của toàn chuỗi, phương án này không tự bảo đảm phát hiện được việc sửa đó.
- Muốn tăng khả năng chống giả mạo cần cân nhắc lưu hash đối chiếu ở nơi độc lập hoặc sử dụng cơ chế ký số phù hợp.

### 2.6. Kết luận

Thử nghiệm cho thấy việc xác minh hash từng bản ghi có thể phát hiện nội dung đã thay đổi nhưng hash chưa được cập nhật. Tuy nhiên, kiểm tra liên kết riêng lẻ vẫn có thể trả về hợp lệ khi bản ghi trước đã bị sửa nội dung nhưng giữ nguyên hash cũ.

Vì vậy, cần xác minh cả hash của từng bản ghi và liên kết toàn chuỗi. Chuỗi hash tự viết không tự ngăn sửa dữ liệu và không bảo đảm phát hiện được người có đủ quyền sửa dữ liệu rồi tính lại toàn bộ hash.

## 3. Phương án 2: Sử dụng quyền PostgreSQL

### 3.1. Mục tiêu

Giới hạn quyền của tài khoản ghi sự kiện để ngăn tài khoản đó cập nhật hoặc xóa những bản ghi đã lưu.

### 3.2. Cách thực hiện

Tạo role `spike_event_writer`, cấp quyền `SELECT` và `INSERT` trên bảng `public.events_test`, sau đó gán role cho `farm_user` để kiểm tra.

### 3.3. Kết quả thử nghiệm

Theo kết quả đã ghi nhận:

- Đọc dữ liệu: thành công.
- Thêm bản ghi: thành công.
- `UPDATE`: bị PostgreSQL từ chối do không đủ quyền.
- `DELETE`: bị PostgreSQL từ chối do không đủ quyền.

### 3.4. Ưu điểm

- Sử dụng cơ chế phân quyền có sẵn của PostgreSQL.
- Hạn chế quyền sửa và xóa của tài khoản ứng dụng.
- Tương đối đơn giản khi cấu hình đúng quyền theo nguyên tắc quyền tối thiểu.

### 3.5. Hạn chế

- Cần cấu hình đúng quyền trên bảng, schema và các đối tượng liên quan.
- Chủ sở hữu bảng hoặc tài khoản quản trị có thể có quyền thay đổi cấu hình hay sửa dữ liệu.
- Phân quyền không tự cung cấp cơ chế phát hiện mọi thay đổi đã xảy ra trong quá khứ.

### 3.6. Kết luận

Trong các trường hợp đã thử, phân quyền PostgreSQL ngăn được thao tác cập nhật và xóa bằng tài khoản bị giới hạn quyền. Cần kiểm tra thêm quyền sở hữu bảng và quyền quản trị để đánh giá đầy đủ phạm vi bảo vệ.

## 4. Phương án 3: Sử dụng PostgreSQL Trigger

### 4.1. Mục tiêu

Từ chối thao tác cập nhật hoặc xóa bản ghi sự kiện đã lưu thông qua các câu lệnh SQL thông thường.

### 4.2. Cách thực hiện

Tạo bảng `public.events_append_test`, hàm `public.prevent_event_mutation()` bằng PL/pgSQL và trigger từ chối các thao tác `UPDATE` và `DELETE`.

### 4.3. Kết quả thử nghiệm

Trong cơ sở dữ liệu kiểm thử `spike_security_test`, đã ghi nhận:

- `INSERT`: thành công, thêm bản ghi sự kiện.
- `UPDATE`: bị từ chối với thông báo `Event records cannot be updated or deleted`.
- `DELETE`: bị từ chối với cùng thông báo.
- `SELECT`: thành công; bản ghi ban đầu vẫn được giữ nguyên.

### 4.4. Ưu điểm

- Quy tắc được thực thi ngay trong cơ sở dữ liệu.
- Ngăn các thao tác cập nhật và xóa thông thường khi trigger đang hoạt động.
- Không phụ thuộc hoàn toàn vào việc giao diện ứng dụng có kiểm tra hay không.

### 4.5. Hạn chế

- Cần tạo, kiểm thử và bảo trì hàm cùng trigger.
- Người có đủ quyền sở hữu hoặc quản trị có thể thay đổi hay vô hiệu hóa cơ chế bảo vệ.
- Trigger không tự bảo đảm chống sửa lén tuyệt đối trong mọi tình huống.

### 4.6. Kết luận

Trong các trường hợp đã thử, trigger cho phép thêm và đọc dữ liệu nhưng từ chối cập nhật và xóa. Cần đánh giá thêm quyền quản trị và khả năng thay đổi cấu hình trigger.

## 5. So sánh tổng quan

| Tiêu chí | Chuỗi hash tự viết | Phân quyền PostgreSQL | PostgreSQL Trigger |
|---|---|---|---|
| Cơ chế chính | Phát hiện thay đổi bằng cách xác minh hash | Giới hạn quyền thao tác | Từ chối thao tác theo quy tắc |
| Phát hiện thay đổi nội dung | Có thể, nếu hash không được cập nhật lại | Không phải chức năng chính | Không phải chức năng chính |
| Ngăn UPDATE/DELETE thông thường | Không tự ngăn | Có, nếu quyền được cấu hình đúng | Có, khi trigger hoạt động |
| Độ phức tạp | Cần tự triển khai và kiểm thử | Thấp đến trung bình | Trung bình |
| Hạn chế chính | Có thể bị tính lại hash | Quyền cao có thể vượt qua giới hạn | Quyền cao có thể thay đổi trigger |

## 6. Nhận xét và hướng đề xuất

Ba phương án giải quyết các khía cạnh khác nhau:

- **Chuỗi hash:** phù hợp khi cần kiểm tra tính toàn vẹn và phát hiện một số thay đổi dữ liệu.
- **Phân quyền PostgreSQL:** phù hợp để giới hạn quyền của tài khoản ứng dụng theo nguyên tắc quyền tối thiểu.
- **PostgreSQL Trigger:** phù hợp để áp dụng quy tắc không cho sửa hoặc xóa thông qua các thao tác SQL thông thường.

Có thể cân nhắc kết hợp phân quyền tối thiểu, trigger và kiểm tra chuỗi hash. Nếu yêu cầu bảo vệ cao hơn, nên lưu bằng chứng đối chiếu ở nơi độc lập hoặc sử dụng cơ chế ký số phù hợp.

Không phương án đơn lẻ nào trong ba phương án bảo đảm chống sửa lén tuyệt đối trước người có toàn quyền quản trị cơ sở dữ liệu.

## 7. Phạm vi và lưu ý kiểm thử

- Phương án 1 được thử nghiệm trên bảng `events_hash_test` trong cơ sở dữ liệu `spike_security_test`.
- Phương án 2 được thử nghiệm trên bảng `events_test`.
- Phương án 3 được thử nghiệm trên bảng `events_append_test` trong cơ sở dữ liệu `spike_security_test`.
- Các bảng trên là những đối tượng kiểm thử riêng biệt.
- Kết quả được ghi nhận dựa trên những phép thử đã thực hiện; không được hiểu là bằng chứng chống sửa lén trong mọi tình huống.
- Phương án 1 đã xác nhận hash của bản ghi số 1 không khớp với nội dung hiện tại. Liên kết của bản ghi số 2 vẫn khớp với hash đang lưu của bản ghi số 1. Cần xác minh cả hash từng bản ghi và liên kết chuỗi khi triển khai thực tế.

## 8. Kết luận chung

Qua các thử nghiệm đã ghi nhận, phân quyền PostgreSQL và trigger có thể hạn chế các thao tác cập nhật, xóa thông thường theo cấu hình tương ứng. Chuỗi hash có thể phát hiện sự không khớp giữa nội dung bản ghi và hash đã lưu, đồng thời cần kiểm tra liên kết giữa các bản ghi.

Việc lựa chọn phương án phụ thuộc vào yêu cầu của hệ thống. Với hệ thống truy xuất chuỗi cung ứng, hướng tiếp cận hợp lý là kết hợp phân quyền tối thiểu, trigger và cơ chế kiểm tra tính toàn vẹn; đồng thời xem xét lưu bằng chứng độc lập nếu cần chống giả mạo ở mức cao hơn.
EOF
