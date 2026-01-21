"""
Legal entity types for NERExtractor config.

These types are used by Semantica NERExtractor to focus extraction
on entities relevant to Vietnamese legal documents.
"""

# Entity types for legal document NER extraction
LEGAL_ENTITY_TYPES = [
    "ORGANIZATION",   # công ty, doanh nghiệp, cơ quan, CTCP, TNHH
    "PERSON_ROLE",    # Giám đốc, TGĐ, thành viên HĐQT, Chủ tịch
    "LEGAL_TERM",     # vốn điều lệ, cổ phần, ĐHĐCĐ, điều lệ
    "MONETARY",       # 10 triệu đồng, 50% vốn điều lệ
    "DURATION",       # 30 ngày, 06 tháng, 1 năm
    "PERCENTAGE",     # 51%, trên 50%, ít nhất 65%
    "CONDITION",      # nếu, trường hợp, khi, trừ trường hợp
    "ACTION",         # thành lập, giải thể, đăng ký, chuyển nhượng
    "PENALTY",        # phạt tiền, đình chỉ hoạt động, tước quyền
]

# Vietnamese prompt for LLM-based NER extraction
LEGAL_NER_PROMPT_VI = """Bạn là chuyên gia trích xuất thực thể từ văn bản pháp luật Việt Nam.

Trích xuất các loại thực thể sau từ văn bản:
- ORGANIZATION: tên công ty, tổ chức, cơ quan (bao gồm viết tắt CTCP, TNHH, DNTN)
- PERSON_ROLE: chức vụ, vai trò (Giám đốc, TGĐ, thành viên HĐQT, Chủ tịch)
- LEGAL_TERM: thuật ngữ pháp lý (vốn điều lệ, cổ phần, ĐHĐCĐ, điều lệ công ty)
- MONETARY: số tiền, giá trị (10 triệu đồng, 50% vốn điều lệ)
- DURATION: thời hạn, kỳ hạn (30 ngày, 06 tháng, trong vòng 1 năm)
- PERCENTAGE: tỷ lệ phần trăm (51%, trên 50%, ít nhất 65%)
- CONDITION: điều kiện áp dụng (nếu, trường hợp, khi, trừ trường hợp)
- ACTION: hành vi pháp lý (thành lập, giải thể, đăng ký, chuyển nhượng)
- PENALTY: hình phạt, chế tài (phạt tiền, đình chỉ hoạt động, tước quyền)

Lưu ý quan trọng:
- Giữ nguyên các từ viết tắt (HĐQT, TGĐ, TNHH, CTCP, ĐHĐCĐ)
- Trích xuất đầy đủ ngữ cảnh số tiền (bao gồm đơn vị tiền tệ)
- Nhận diện điều kiện kép (nếu... và..., trường hợp... hoặc...)
- Phân biệt rõ ACTION (hành động) và CONDITION (điều kiện)

Văn bản cần trích xuất:
{text}

Trả về JSON array với format:
[{{"text": "...", "label": "ENTITY_TYPE", "start_char": N, "end_char": M}}]
"""

# Known abbreviations for context (from Phase 03.5)
LEGAL_ABBREVIATIONS = {
    "HĐQT": "Hội đồng quản trị",
    "HĐTV": "Hội đồng thành viên",
    "ĐHĐCĐ": "Đại hội đồng cổ đông",
    "TGĐ": "Tổng giám đốc",
    "GĐ": "Giám đốc",
    "BKS": "Ban kiểm soát",
    "KSV": "Kiểm soát viên",
    "CTCP": "Công ty cổ phần",
    "TNHH": "Trách nhiệm hữu hạn",
    "DNTN": "Doanh nghiệp tư nhân",
    "HTX": "Hợp tác xã",
    "GCNĐKKD": "Giấy chứng nhận đăng ký kinh doanh",
    "GCNĐKDN": "Giấy chứng nhận đăng ký doanh nghiệp",
}
