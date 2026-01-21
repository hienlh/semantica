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

# Known abbreviations for context (expanded from Phase 03.5)
LEGAL_ABBREVIATIONS = {
    # Organization roles
    "HĐQT": "Hội đồng quản trị",
    "HĐTV": "Hội đồng thành viên",
    "ĐHĐCĐ": "Đại hội đồng cổ đông",
    "TGĐ": "Tổng giám đốc",
    "GĐ": "Giám đốc",
    "BKS": "Ban kiểm soát",
    "KSV": "Kiểm soát viên",
    "CT": "Chủ tịch",
    "PCT": "Phó Chủ tịch",
    # Company types
    "CTCP": "Công ty cổ phần",
    "TNHH": "Trách nhiệm hữu hạn",
    "DNTN": "Doanh nghiệp tư nhân",
    "HTX": "Hợp tác xã",
    "DN": "Doanh nghiệp",
    # Registration/Legal terms
    "GCNĐKKD": "Giấy chứng nhận đăng ký kinh doanh",
    "GCNĐKDN": "Giấy chứng nhận đăng ký doanh nghiệp",
    "ĐKKD": "Đăng ký kinh doanh",
    "ĐKDN": "Đăng ký doanh nghiệp",
    "VĐL": "Vốn điều lệ",
    # Government agencies
    "UBND": "Ủy ban nhân dân",
    "HĐND": "Hội đồng nhân dân",
    "CP": "Chính phủ",
    "QH": "Quốc hội",
    "BTC": "Bộ Tài chính",
    "BKHĐT": "Bộ Kế hoạch và Đầu tư",
    # Legal documents
    "NĐ": "Nghị định",
    "TT": "Thông tư",
    "QĐ": "Quyết định",
    "NQ": "Nghị quyết",
}
