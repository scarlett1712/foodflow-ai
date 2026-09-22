# 🎬 KỊCH BẢN THUYẾT TRÌNH & DEMO DỰ ÁN: FOODFLOW AI

> **Dự án:** FoodFlow AI — Intelligent F&B Inventory & Supply Chain Optimization with Solana Audit Layer  
> **Thời lượng:** Có 3 phiên bản lựa chọn (30 giây Elevator Pitch, 3 phút Pitching Hackathon, 5 phút Video Demo Walkthrough)  
> **Ngôn ngữ:** Tiếng Việt (kèm thuật ngữ công nghệ quốc tế)

---

## ⚡ PHIÊN BẢN 1: ELEVATOR PITCH (30 GIÂY)
*(Dùng khi gặp nhanh Giám khảo, Nhà đầu tư hoặc mở đầu bài phỏng vấn)*

> *"Xin chào Ban giám khảo, ở Việt Nam mỗi năm ngành F&B thất thoát hơn **30.000 tỷ đồng** chỉ vì hai việc: **dự đoán đi chợ bằng cảm tính** gây hư hỏng thực phẩm, và **gian lận, sửa lùi ngày hạn dùng (FEFO)** trong kho.*  
>  
> *Chúng tôi tạo ra **FoodFlow AI** — giải pháp kiến trúc kép: **Off-chain AI** dùng XGBoost kết hợp bóc tách định lượng BOM để dự báo chính xác từng lạng thịt, kg rau cần mua mỗi ngày; kết hợp với **On-chain Solana** để khóa bất biến hạn sử dụng lô hàng và tạo **bằng chứng cam kết kép (Dual-Commitment Proof)** chống gian lận mua hàng.*  
>  
> *FoodFlow AI giúp giảm **25% lãng phí nguyên liệu**, tiết kiệm **15% chi phí mua hàng** và bảo đảm an toàn vệ sinh thực phẩm 100% minh bạch."*

---

## 🎤 PHIÊN BẢN 2: PITCHING TRANH TÀI HACKATHON (3 PHÚT)
*(Dành cho vòng thuyết trình sân khấu hoặc chấm thi Demo Day)*

### ⏱️ [00:00 - 00:35] MỞ ĐẦU: NỖI ĐAU THỰC TẾ (THE HOOK & PROBLEM)
- **Hành động:** Chiếu slide / màn hình trang chủ FoodFlow AI. Giọng nói tự tin, nhấn mạnh con số.
- **Lời thoại:**
  > *"Kính thưa Ban giám khảo và toàn thể hội trường,*  
  > *Mỗi buổi sáng lúc 4 giờ, hàng chục nghìn chủ quán ăn và quản lý nhà hàng F&B tại Việt Nam đều phải đối mặt với cùng một câu hỏi đau đầu:* **'Hôm nay đi chợ mua bao nhiêu kg thịt bò, bao nhiêu kg rau?'**  
  >  
  > *Mua thừa thì tối vứt bỏ vào thùng rác — ăn mòn lợi nhuận biên vốn chỉ mỏng manh 10-15%. Mua thiếu thì khách vào gọi món đành báo 'hết hàng' — mất khách.*  
  > *Nghiêm trọng hơn, khi mở chuỗi từ 3 chi nhánh trở lên, chủ nhà hàng hoàn toàn mất kiểm soát: Quản lý chi nhánh có thể cấu kết sửa lùi hạn dùng của lô hàng cũ, hoặc kê khống giá mua thực phẩm ngoài chợ mà không có bằng chứng đối soát.*  
  >  
  > *Hôm nay, chúng tôi mang đến câu trả lời: **FoodFlow AI** — Nền tảng AI tối ưu chuỗi cung ứng F&B kết hợp lớp kiểm toán bất biến trên Solana."*

---

### ⏱️ [00:35 - 01:15] GIẢI PHÁP: KIẾN TRÚC 2 TẦNG (OFF-CHAIN AI + ON-CHAIN SOLANA)
- **Hành động:** Chiếu sơ đồ kiến trúc hệ thống 2 tầng (Off-chain & On-chain).
- **Lời thoại:**
  > *"FoodFlow AI giải quyết triệt để bài toán này bằng kiến trúc 2 tầng độc đáo:*  
  >  
  > *1. **Ở tầng Off-Chain:** Chúng tôi xây dựng mô hình **XGBoost Global Model**, tích hợp đặc thù F&B Việt Nam: chu kỳ tuần hoàn 7 ngày, hiệu ứng ngày lễ dương lịch và 6 đặc trưng lịch Tết âm lịch. AI dự báo lượng bán từng món ăn, sau đó tự động **bóc tách định lượng (BOM Recipes)** ra chính xác từng gram nguyên liệu cần đi chợ, kết hợp đệm tồn kho an toàn (Safety Stock).*  
  >  
  > *2. **Ở tầng On-Chain:** Thay vì chỉ làm phần mềm quản lý nội bộ dễ bị chỉnh sửa database, chúng tôi đưa **Solana Devnet** vào làm lớp kiểm toán bất biến (Immutable Audit Trail) với tốc độ cao và chi phí siêu rẻ."*

---

### ⏱️ [01:15 - 02:15] TRÌNH DIỄN SẢN PHẨM THỰC TẾ (LIVE PRODUCT DEMO)
- **Hành động:** Thao tác trực tiếp trên giao diện [http://localhost:5173](http://localhost:5173).

#### Phân cảnh 1: Dự báo nhu cầu & Gợi ý đi chợ
- **Thao tác:** Bấm vào tab **Dự Báo & Gợi Ý Mua Hàng**, chọn Chi Nhánh 01.
- **Lời thoại:**
  > *"Như ban giám khảo thấy trên màn hình, ngày mai hệ thống dự báo món Phở Bò Tái Nạm sẽ tiêu thụ 110 bát. AI tự động nhân với định lượng công thức: 0.15kg thịt bò, 0.25kg bánh phở tươi. Đối chiếu với số dư kho hiện có, hệ thống lập tức xuất ra **Đơn mua hàng đề xuất**: Cần mua gấp 14.5 kg thịt bò nạm, cảnh báo màu đỏ mức Thiếu khẩn cấp."*

#### Phân cảnh 2: AI Thẩm định chênh lệch (Variance Evaluator)
- **Thao tác:** Nhập thực tế mua 18 kg (vượt 3.5 kg) và nhập lý do: *"Hôm nay trời bão, rau khan hiếm, chuẩn bị cho tiệc công ty 20 khách"*.
- **Lời thoại:**
  > *"Khi quản lý đi chợ mua vượt định mức, hệ thống kích hoạt **AI Variance Evaluator**. Mô hình phân tích ngôn ngữ tự nhiên nhận diện lý do 'trời bão' và 'tiệc công ty', đánh giá mức độ hợp lý **95%**, tự động phân loại 'Biến động thị trường' và thích ứng hạn mức cho tuần tới mà không bị phạt."*

#### Phân cảnh 3: Bằng chứng kép Solana (Dual-Commitment Proof)
- **Thao tác:** Bấm nút **'Xác Nhận Đi Chợ & Chứng Thực Solana'** $\rightarrow$ Bật popup **Solana Verification Modal** $\rightarrow$ Click link mở Solana Explorer.
- **Lời thoại:**
  > *"Ngay khi bấm xác nhận, hệ thống tính toán mã băm SHA-256 đóng gói: Kế hoạch AI + Số thực mua + Lý do giải trình + Phán quyết của AI thành **Bằng chứng kép (Dual-Commitment)** và ký xác thực on-chain lên Solana qua Anchor Program.*  
  > *Mọi dữ liệu hạn dùng FEFO và đơn mua đều là vĩnh cửu, không một quản lý hay lập trình viên nào có thể xóa sửa database để gian lận."*

---

### ⏱️ [02:15 - 03:00] TÁC ĐỘNG NGHIỆP VỤ & TẦNG NHÌN (IMPACT & VISION)
- **Hành động:** Chuyển về slide tổng kết số liệu và roadmap.
- **Lời thoại:**
  > *"Thực nghiệm trên tập dữ liệu 2 năm với 3 chi nhánh và 22 món ăn cho thấy:*  
  > - *Mô hình XGBoost giúp giảm sai số **WAPE xuống dưới 12%**, vượt trội hoàn toàn so với cách tính trung bình tay truyền thống (24-28%).*  
  > - *Cắt giảm **20-25% lãng phí hủy hàng** do hết hạn nhờ quản lý hạn dùng FEFO.*  
  > - *Chi phí kiểm toán chuỗi cung ứng bằng 0 nhờ khả năng xử lý hàng nghìn giao dịch mỗi giây của Solana.*  
  >  
  > *FoodFlow AI không chỉ là một công cụ dự báo, mà là **hệ điều hành thông minh và minh bạch hóa toàn bộ chuỗi cung ứng F&B**.  
  > Xin cảm ơn Ban giám khảo, chúng tôi sẵn sàng cho phần Q&A!"*

---

## 📹 PHIÊN BẢN 3: KỊCH BẢN QUAY VIDEO DEMO SẢN PHẨM (5 PHÚT)
*(Chi tiết từng phân cảnh, visual cues, thao tác chuột cho video nộp bài)*

| Thời lượng | Cảnh quay (Visual / Screen Action) | Lời thoại thuyết minh (Voiceover Script) |
| :--- | :--- | :--- |
| **00:00 - 00:45** | **Cảnh 1: Giới thiệu & Dashboard tổng quan**<br>• Mở trang chủ [Dashboard](http://localhost:5173/)<br>• Rê chuột qua 4 thẻ KPI: Doanh thu dự kiến, Chi phí nguyên liệu, Số mặt hàng thiếu hụt, Đơn hàng Solana đã chứng thực. | *"Chào mừng bạn đến với FoodFlow AI — giải pháp ứng dụng Trí tuệ nhân tạo và Blockchain Solana để cách mạng hóa quản lý chuỗi cung ứng ngành F&B. Tại màn hình Dashboard, nhà quản trị có cái nhìn 360 độ về tình trạng vận hành của toàn chuỗi: từ doanh thu dự kiến, lượng tồn kho đến các cảnh báo thiếu hụt nguyên liệu trong ngày."* |
| **00:45 - 01:45** | **Cảnh 2: Trung tâm Dữ liệu & Dự báo XGBoost**<br>• Chuyển sang trang **Dự Báo Nhu Cầu**<br>• Chọn bộ lọc Chi nhánh: Cầu Giấy, chọn khung thời gian 7 ngày.<br>• Phóng to biểu đồ so sánh: Baseline Moving Average vs XGBoost Model v2. | *"Trái tim của hệ thống là mô hình XGBoost Global Model. Khác với các thuật toán trung bình trượt thông thường, mô hình của FoodFlow AI học sâu trên 66 chuỗi thời gian, tích hợp lịch nghỉ lễ Việt Nam và 6 đặc trưng Tết Nguyên Đán. Nhờ vậy, mô hình dự báo chính xác nhu cầu từng món trong 7 ngày tới, bám sát các đợt bùng nổ đơn hàng cuối tuần và đơn đặt tiệc trước."* |
| **01:45 - 02:45** | **Cảnh 3: Gợi Ý Đi Chợ Tự Động (BOM & Safety Stock)**<br>• Chuyển sang trang **Gợi Ý Mua Hàng**<br>• Xem bảng quy đổi nguyên liệu (thịt bò, gạo thơm, bún...).<br>• Chỉ rõ cột: Cần dùng $\rightarrow$ Tồn kho $\rightarrow$ Đề xuất mua $\rightarrow$ Trạng thái (Critical đỏ, Warning vàng). | *"Từ dự báo món ăn, dịch vụ Recommendation tự động bóc tách định lượng theo bảng công thức món (BOM Recipes). Thay vì nhân viên phải tính nhẩm, hệ thống tự động đối chiếu tồn kho thực tế, áp dụng đệm an toàn Safety Stock và lập ngay 'Danh sách đi chợ' tối ưu: chỉ mua đúng lượng thiếu hụt, tránh ứ đọng vốn."* |
| **02:45 - 03:50** | **Cảnh 4: Thẩm định chênh lệch AI & Ký số Solana**<br>• Mở modal **Xác Nhận Mua Hàng**<br>• Thay đổi số lượng mua cao hơn mức AI đề xuất.<br>• Nhập lý do giải trình: 'Giá thịt tăng do mưa bão, gom thêm hàng sỉ'.<br>• Xem AI chấm điểm tính hợp lý (Plausibility: 92%).<br>• Nhấp nút **Chứng thực On-chain**. | *"Khi nhân viên đi chợ về và có biến động về giá hoặc số lượng, mô hình AI Variance Evaluator sẽ phân tích lý do giải trình qua xử lý ngôn ngữ tự nhiên. Nếu hợp lý, hệ thống tự điều chỉnh giá vốn chuẩn cho tuần sau. Toàn bộ đơn mua hàng kèm lý do giải trình và kết luận của AI được băm SHA-256 để tạo 'Bằng chứng cam kết kép' (Dual-Commitment Proof) và ký phát hành lên Solana Devnet."* |
| **03:50 - 04:35** | **Cảnh 5: Quản lý Kho Hạn Dùng FEFO & Đối soát On-Chain**<br>• Mở trang **Kho Hàng & Lô Hàng FEFO**<br>• Xem các lô hàng có hạn sử dụng, trạng thái CONFIRMED.<br>• Nhấp vào một lô hàng $\rightarrow$ Mở popup Solana Verification $\rightarrow$ Click link ra Solana Explorer. | *"Tại kho hàng, từng lô nguyên liệu được quản lý theo cơ chế FEFO: ưu tiên xuất kho lô sắp hết hạn trước. Mỗi mã lô hàng và ngày hết hạn đều được khóa vĩnh viễn trên Solana PDA. Khi mở Solana Explorer, bất kỳ ai cũng có thể kiểm chứng thời điểm nhập kho và chữ ký mật mã không thể làm giả."* |
| **04:35 - 05:00** | **Cảnh 6: Kết luận & Kêu gọi hành động**<br>• Quay lại Dashboard tổng kết.<br>• Hiện logo FoodFlow AI + thông tin liên hệ / repo GitHub. | *"FoodFlow AI: Chuẩn hóa quy trình đi chợ bằng AI — Minh bạch hóa chuỗi cung ứng bằng Solana. Giải pháp sẵn sàng triển khai cho các chuỗi F&B từ quy mô vừa đến lớn. Xin chân thành cảm ơn!"* |

---

## 🧠 BỘ CÂU HỎI VÀ TRẢ LỜI ĐỐI PHÓ GIÁM KHẢO (CHEF / TECH Q&A)

### Câu 1: *"Tại sao phải dùng Blockchain/Solana? Cơ sở dữ liệu SQLite/Postgres bình thường không đủ à?"*
> **Trả lời:**  
> *"Dạ thưa Giám khảo, nếu chỉ để lưu trữ thông thường thì cơ sở dữ liệu truyền thống là đủ. Nhưng trong chuỗi cung ứng F&B, vấn đề sống còn là **Niềm tin và Tính bất biến (Trust & Immutability)**:*  
> *1. **Chống sửa hạn dùng (FEFO Tamper-proofing):** Khi quản lý chi nhánh để thịt cá quá hạn, họ có thể chỉnh sửa ngày trong database nội bộ để che mắt thanh tra vệ sinh hoặc chủ chuỗi. Khi đã băm và ký PDA trên Solana, ngày hết hạn là bất biến.*  
> *2. **Bằng chứng cam kết kép (Dual-Commitment):** Chủ chuỗi cần bằng chứng minh bạch rằng nhân viên đã mua lệch kế hoạch vì lý do gì và AI đã duyệt ra sao, đảm bảo dữ liệu phục vụ đối soát tài chính không thể bị xóa bỏ.*  
> *Chúng tôi chọn Solana vì thông lượng giao dịch cao và phí giao dịch chỉ $0.00025, hoàn toàn khả thi về mặt kinh tế cho các đơn hàng F&B hàng ngày."*

### Câu 2: *"Mô hình AI XGBoost có gì đặc biệt so với các giải pháp trên thị trường?"*
> **Trả lời:**  
> *"Mô hình của FoodFlow AI là **Global Model v2**, được thiết kế đo ni đóng giày cho thị trường F&B Việt Nam:*  
> *- Sử dụng tính năng `enable_categorical=True` của XGBoost để học mối tương quan chéo giữa các chi nhánh và món ăn mà không làm phình chiều dữ liệu.*  
> *- Tích hợp bộ đặc trưng lịch âm và Tết Nguyên Đán (giai đoạn tất niên, mùng 1-3 Tết) — yếu tố gây sai lệch dự báo lớn nhất trong năm của ngành F&B Việt Nam.*  
> *- Kết quả thực nghiệm cho thấy WAPE giảm từ mức 28% của baseline xuống chỉ còn **10-12%**."*

### Câu 3: *"Nếu nhà hàng có 100 chi nhánh, chi phí lưu trữ trên Solana có bị đắt không?"*
> **Trả lời:**  
> *"Dạ hiện tại trên Devnet chúng tôi sử dụng Anchor PDA để lưu dữ liệu kiểm toán. Khi lên Mainnet production, để tối ưu hóa chi phí thuê tài khoản (Rent-exemption), chúng tôi đã có giải pháp kiến trúc:*  
> *- Ứng dụng **Solana State Compression (Compressed Accounts / Bubblegum)** băm dữ liệu vào cây Merkle Tree On-chain, giúp chi phí ghi dữ liệu giảm hơn 1.000 lần, chỉ tốn vài cent cho hàng chục nghìn lô hàng mỗi tháng.*  
> *- Hoặc cơ chế đóng tài khoản PDA (`close account`) khi lô hàng đã tiêu thụ xong để hoàn lại tiền cọc Rent cho ví nhà hàng."*
