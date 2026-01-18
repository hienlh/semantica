"""
Legal domain entity types for Vietnamese legal document NER extraction.

Entity types designed for:
- Vietnamese legal documents (Luật, Nghị định, Thông tư)
- Corporate law focus (Luật Doanh nghiệp)
- Support for both Vietnamese abbreviations and full forms

These entity types are used by LegalNERExtractor for extracting
domain-specific entities from legal text.
"""

from enum import Enum
from typing import Dict, List


class LegalEntityType(Enum):
    """Entity types for Vietnamese legal documents."""

    # Organizations & Legal Entities
    ORGANIZATION = "ORGANIZATION"  # doanh nghiệp, công ty, tổ chức, cơ quan

    # Persons & Roles
    PERSON_ROLE = "PERSON_ROLE"  # Giám đốc, TGĐ, thành viên HĐQT, Chủ tịch

    # Legal Terms & Concepts
    LEGAL_TERM = "LEGAL_TERM"  # vốn điều lệ, cổ phần, ĐHĐCĐ, hợp đồng

    # Quantities & Values
    MONETARY = "MONETARY"  # 10 triệu đồng, 50% vốn điều lệ
    PERCENTAGE = "PERCENTAGE"  # 51%, trên 50%, dưới 35%
    DURATION = "DURATION"  # 30 ngày, 06 tháng, 2 năm

    # Logic & Conditions
    CONDITION = "CONDITION"  # nếu, trường hợp, khi, trừ trường hợp

    # Actions & Activities
    ACTION = "ACTION"  # thành lập, giải thể, đăng ký, chuyển nhượng

    # Consequences & Penalties
    PENALTY = "PENALTY"  # phạt tiền, đình chỉ hoạt động, tước quyền


# Entity types list for NERExtractor config
LEGAL_ENTITY_TYPES: List[str] = [e.value for e in LegalEntityType]


# Vietnamese regex patterns for entity extraction (pattern-based fallback)
ENTITY_PATTERNS: Dict[LegalEntityType, List[str]] = {
    LegalEntityType.ORGANIZATION: [
        # Full forms
        r"(công ty(?:\s+(?:cổ phần|TNHH|hợp danh|tư nhân))?)",
        r"(doanh nghiệp(?:\s+(?:nhà nước|tư nhân|có vốn đầu tư nước ngoài))?)",
        r"(tổ chức(?:\s+(?:kinh tế|tín dụng|phi lợi nhuận))?)",
        r"(cơ quan(?:\s+(?:nhà nước|quản lý))?)",
        r"(hợp tác xã)",
        r"(chi nhánh)",
        r"(văn phòng đại diện)",
        # Common abbreviations
        r"\b(CTCP|TNHH|DNTN|DNNN|HTX)\b",
    ],
    LegalEntityType.PERSON_ROLE: [
        # Full forms
        r"((?:Chủ tịch|Phó Chủ tịch)(?:\s+(?:Hội đồng quản trị|Hội đồng thành viên|công ty))?)",
        r"((?:Giám đốc|Phó giám đốc|Tổng giám đốc|Phó Tổng giám đốc))",
        r"((?:thành viên|Thành viên)(?:\s+(?:Hội đồng quản trị|Hội đồng thành viên|Ban kiểm soát))?)",
        r"((?:cổ đông|Cổ đông)(?:\s+(?:sáng lập|lớn|nhỏ))?)",
        r"((?:người|Người)(?:\s+(?:đại diện theo pháp luật|quản lý|điều hành)))",
        r"((?:Kiểm soát viên|kiểm soát viên))",
        r"((?:Kế toán trưởng|kế toán trưởng))",
        # Common abbreviations
        r"\b(GĐ|TGĐ|HĐQT|HĐTV|BKS|KSV|ĐHĐCĐ)\b",
    ],
    LegalEntityType.LEGAL_TERM: [
        r"(vốn(?:\s+(?:điều lệ|góp|pháp định|chủ sở hữu)))",
        r"(cổ phần(?:\s+(?:phổ thông|ưu đãi|biểu quyết))?)",
        r"(phần vốn góp)",
        r"((?:Điều lệ|điều lệ)(?:\s+công ty)?)",
        r"(giấy(?:\s+(?:chứng nhận đăng ký doanh nghiệp|phép kinh doanh))?)",
        r"(hợp đồng(?:\s+(?:lao động|thương mại|dân sự))?)",
        r"(biên bản(?:\s+(?:họp|nghị quyết))?)",
        r"(quyền(?:\s+(?:sở hữu|sử dụng|biểu quyết))?)",
        r"(nghĩa vụ(?:\s+(?:tài chính|thuế))?)",
        # Abbreviations
        r"\b(GCNĐKDN|ĐKKD|HĐLĐ)\b",
    ],
    LegalEntityType.MONETARY: [
        # Amounts with units
        r"(\d+(?:[.,]\d+)?(?:\s+(?:triệu|tỷ|nghìn|tỉ))?\s*(?:đồng|VND|USD|EUR))",
        # Percentage of capital
        r"(\d+(?:[.,]\d+)?\s*%\s*(?:vốn|vốn điều lệ|tổng vốn|giá trị))",
        # Written amounts
        r"((?:trên|dưới|ít nhất|tối thiểu|tối đa)\s+\d+(?:[.,]\d+)?\s*(?:triệu|tỷ)\s*(?:đồng|VND)?)",
    ],
    LegalEntityType.PERCENTAGE: [
        r"(\d+(?:[.,]\d+)?\s*%)",
        r"((?:trên|dưới|ít nhất|hơn|không quá)\s+\d+(?:[.,]\d+)?\s*%)",
        r"((?:quá bán|đa số|toàn bộ|một phần)(?:\s+\d+(?:[.,]\d+)?\s*%)?)",
    ],
    LegalEntityType.DURATION: [
        r"((?:trong\s+)?(?:thời hạn\s+)?(\d+)\s*(ngày|tháng|năm|giờ|tuần))",
        r"((?:không quá|tối đa|ít nhất|tối thiểu)\s+(\d+)\s*(ngày|tháng|năm))",
        r"((?:trước|sau)\s+(\d+)\s*(ngày|tháng|năm))",
        r"((\d+)\s*ngày\s*(?:làm việc|kể từ|trước khi|sau khi))",
    ],
    LegalEntityType.CONDITION: [
        r"((?:nếu|Nếu)(?:\s+như)?)",
        r"((?:trường hợp|Trường hợp)(?:\s+(?:nếu|này|khác|đặc biệt))?)",
        r"((?:khi|Khi)(?:\s+(?:nào|đó))?)",
        r"((?:trừ|Trừ)(?:\s+(?:trường hợp|khi|phi))?)",
        r"((?:trong trường hợp|Trong trường hợp))",
        r"((?:với điều kiện|Với điều kiện))",
        r"((?:miễn là|Miễn là))",
    ],
    LegalEntityType.ACTION: [
        r"(thành lập(?:\s+(?:công ty|doanh nghiệp))?)",
        r"(giải thể(?:\s+(?:công ty|doanh nghiệp))?)",
        r"((?:đăng ký|Đăng ký)(?:\s+(?:kinh doanh|doanh nghiệp|thay đổi))?)",
        r"((?:chuyển nhượng|Chuyển nhượng)(?:\s+(?:cổ phần|vốn|quyền))?)",
        r"(sáp nhập(?:\s+(?:công ty|doanh nghiệp))?)",
        r"((?:chia|tách|hợp nhất)(?:\s+(?:công ty|doanh nghiệp))?)",
        r"((?:mua lại|Mua lại)(?:\s+(?:cổ phần|doanh nghiệp))?)",
        r"((?:phá sản|Phá sản))",
        r"((?:thanh lý|Thanh lý)(?:\s+(?:tài sản|công ty))?)",
    ],
    LegalEntityType.PENALTY: [
        r"(phạt\s+tiền(?:\s+(?:từ|đến|tối đa|tối thiểu))?\s*\d*(?:[.,]\d+)?\s*(?:triệu|tỷ)?(?:\s*đồng)?)",
        r"(đình chỉ(?:\s+(?:hoạt động|kinh doanh|thi công))?)",
        r"((?:tước|thu hồi)(?:\s+(?:quyền|giấy phép|chứng chỉ))?)",
        r"((?:cấm|Cấm)(?:\s+(?:kinh doanh|hoạt động|hành nghề))?)",
        r"((?:buộc|Buộc)(?:\s+(?:bồi thường|khắc phục|chấm dứt))?)",
        r"((?:truy cứu|Truy cứu)(?:\s+trách nhiệm(?:\s+(?:hình sự|dân sự))?)?)",
    ],
}


# LLM prompt hints for better extraction (Vietnamese)
ENTITY_EXTRACTION_PROMPT_VI = """
Bạn là chuyên gia trích xuất thực thể từ văn bản pháp luật Việt Nam.

Trích xuất các loại thực thể sau từ văn bản:

1. **ORGANIZATION** - Tổ chức, doanh nghiệp, cơ quan:
   - Công ty, doanh nghiệp, tổ chức, cơ quan nhà nước
   - Viết tắt: CTCP, TNHH, DNTN, HTX

2. **PERSON_ROLE** - Chức vụ, vai trò:
   - Giám đốc, Tổng giám đốc, Chủ tịch HĐQT
   - Viết tắt: GĐ, TGĐ, HĐQT, HĐTV, BKS

3. **LEGAL_TERM** - Thuật ngữ pháp lý:
   - Vốn điều lệ, cổ phần, phần vốn góp, điều lệ
   - Giấy chứng nhận đăng ký doanh nghiệp

4. **MONETARY** - Số tiền, giá trị:
   - 10 triệu đồng, 50 tỷ VND
   - 50% vốn điều lệ

5. **PERCENTAGE** - Tỷ lệ phần trăm:
   - 51%, trên 35%, dưới 50%

6. **DURATION** - Thời hạn, kỳ hạn:
   - 30 ngày, 06 tháng, 2 năm

7. **CONDITION** - Điều kiện:
   - nếu, trường hợp, khi, trừ trường hợp

8. **ACTION** - Hành động pháp lý:
   - thành lập, giải thể, đăng ký, chuyển nhượng

9. **PENALTY** - Hình phạt, chế tài:
   - phạt tiền, đình chỉ hoạt động, tước quyền

Lưu ý quan trọng:
- Giữ nguyên viết tắt (HĐQT, TGĐ, TNHH)
- Trích xuất đầy đủ ngữ cảnh số tiền (bao gồm đơn vị)
- Nhận diện điều kiện kép (nếu... và...)
- Phân biệt rõ thực thể với từ thông thường

Văn bản cần phân tích:
{text}

Trả về JSON với format:
[
  {{"text": "HĐQT", "type": "PERSON_ROLE", "start": 10, "end": 14}},
  {{"text": "10 triệu đồng", "type": "MONETARY", "start": 50, "end": 63}}
]
"""

# Common abbreviation mappings for entity type disambiguation
ABBREVIATION_TO_ENTITY_TYPE: Dict[str, LegalEntityType] = {
    # Organization abbreviations
    "CTCP": LegalEntityType.ORGANIZATION,
    "TNHH": LegalEntityType.ORGANIZATION,
    "DNTN": LegalEntityType.ORGANIZATION,
    "DNNN": LegalEntityType.ORGANIZATION,
    "HTX": LegalEntityType.ORGANIZATION,
    # Person/Role abbreviations
    "GĐ": LegalEntityType.PERSON_ROLE,
    "TGĐ": LegalEntityType.PERSON_ROLE,
    "HĐQT": LegalEntityType.PERSON_ROLE,
    "HĐTV": LegalEntityType.PERSON_ROLE,
    "BKS": LegalEntityType.PERSON_ROLE,
    "KSV": LegalEntityType.PERSON_ROLE,
    "ĐHĐCĐ": LegalEntityType.PERSON_ROLE,
    # Legal term abbreviations
    "GCNĐKDN": LegalEntityType.LEGAL_TERM,
    "ĐKKD": LegalEntityType.LEGAL_TERM,
    "HĐLĐ": LegalEntityType.LEGAL_TERM,
}
