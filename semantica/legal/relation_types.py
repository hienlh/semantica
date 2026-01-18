"""
Legal domain relation types for Vietnamese legal document relation extraction.

Relation types designed for:
- Vietnamese legal documents (Luật, Nghị định, Thông tư)
- Cross-reference relationships between articles
- Semantic relationships in corporate law

These relation types are used by LegalRelationExtractor for extracting
domain-specific relations from legal text.
"""

from enum import Enum
from typing import Dict, List


class LegalRelationType(Enum):
    """Relation types for Vietnamese legal documents."""

    # Prerequisite/Dependency Relations
    REQUIRES = "REQUIRES"  # X requires Y (điều kiện tiên quyết)
    DEPENDS_ON = "DEPENDS_ON"  # X depends on Y

    # Consequence Relations
    HAS_PENALTY = "HAS_PENALTY"  # violation has penalty
    RESULTS_IN = "RESULTS_IN"  # action results in consequence

    # Scope Relations
    APPLIES_TO = "APPLIES_TO"  # rule applies to subject
    EXCLUDES = "EXCLUDES"  # rule excludes subject

    # Conditional Relations
    CONDITION_FOR = "CONDITION_FOR"  # condition for action

    # Definition Relations
    DEFINED_AS = "DEFINED_AS"  # term defined as
    INCLUDES = "INCLUDES"  # definition includes

    # Cross-Reference Relations (from Phase 03)
    REFERENCES = "REFERENCES"  # article references another
    AMENDS = "AMENDS"  # article amends another
    SUPERSEDES = "SUPERSEDES"  # article supersedes another
    IMPLEMENTS = "IMPLEMENTS"  # article implements (huong dan thi hanh)

    # Structural Relations
    CONTAINS = "CONTAINS"  # document contains chapter/article
    PART_OF = "PART_OF"  # clause is part of article

    # Authority Relations
    AUTHORIZED_BY = "AUTHORIZED_BY"  # action authorized by entity
    PERFORMED_BY = "PERFORMED_BY"  # action performed by role


# Relation types list for RelationExtractor config
LEGAL_RELATION_TYPES: List[str] = [r.value for r in LegalRelationType]


# Vietnamese patterns for relation detection
RELATION_PATTERNS: Dict[LegalRelationType, List[str]] = {
    LegalRelationType.REQUIRES: [
        r"để\s+(.+?)\s+phải\s+(.+)",
        r"điều kiện\s+để\s+(.+?)\s+là\s+(.+)",
        r"yêu cầu\s+(.+?)\s+phải\s+(.+)",
        r"bắt buộc\s+(.+?)\s+phải\s+(.+)",
        r"cần\s+có\s+(.+?)\s+để\s+(.+)",
    ],
    LegalRelationType.HAS_PENALTY: [
        r"vi phạm\s+(.+?)\s+(?:bị\s+)?(?:phạt|xử phạt)\s+(.+)",
        r"hành vi\s+(.+?)\s+(?:bị\s+)?(?:phạt|xử lý)\s+(.+)",
        r"(.+?)\s+bị\s+(?:phạt tiền|đình chỉ|tước quyền)\s+(.+)",
        r"trường hợp\s+(.+?)\s+sẽ\s+bị\s+(.+)",
    ],
    LegalRelationType.APPLIES_TO: [
        r"(?:quy định\s+)?(?:này\s+)?áp dụng\s+(?:cho|đối với)\s+(.+)",
        r"(.+?)\s+(?:được\s+)?áp dụng\s+(?:cho|đối với)\s+(.+)",
        r"điều\s+(?:này|luật\s+này)\s+(?:được\s+)?áp dụng\s+(.+)",
    ],
    LegalRelationType.EXCLUDES: [
        r"(?:quy định\s+)?(?:này\s+)?không\s+áp dụng\s+(?:cho|đối với)\s+(.+)",
        r"trừ\s+(?:trường hợp\s+)?(.+)",
        r"ngoại trừ\s+(.+)",
        r"không\s+bao gồm\s+(.+)",
    ],
    LegalRelationType.CONDITION_FOR: [
        r"(?:nếu|khi)\s+(.+?)\s+thì\s+(.+)",
        r"trong\s+trường\s+hợp\s+(.+?)\s+thì\s+(.+)",
        r"với\s+điều\s+kiện\s+(.+?)\s+(.+)",
    ],
    LegalRelationType.DEFINED_AS: [
        r"(.+?)\s+là\s+(.+)",
        r"(.+?)\s+được\s+(?:hiểu|định nghĩa)\s+là\s+(.+)",
        r"(.+?)\s+có\s+nghĩa\s+là\s+(.+)",
        r"(?:thuật ngữ\s+)?(.+?)\s+(?:được\s+)?giải thích\s+(.+)",
    ],
    LegalRelationType.INCLUDES: [
        r"(.+?)\s+bao\s+gồm\s+(.+)",
        r"(.+?)\s+gồm\s+(?:có\s+)?(.+)",
        r"(.+?)\s+bao\s+hàm\s+(.+)",
    ],
    LegalRelationType.REFERENCES: [
        r"theo\s+(?:quy\s+định\s+)?(?:tại\s+)?Điều\s+(\d+)",
        r"căn\s+cứ\s+(?:vào\s+)?(?:Điều|Khoản)\s+(.+)",
        r"quy\s+định\s+tại\s+(?:Điều|Khoản)\s+(.+)",
        r"nêu\s+tại\s+(?:Điều|Khoản)\s+(.+)",
    ],
    LegalRelationType.AMENDS: [
        r"sửa\s+đổi\s+(?:bổ\s+sung\s+)?(.+)",
        r"thay\s+đổi\s+(?:nội\s+dung\s+)?(.+)",
        r"bổ\s+sung\s+(.+)",
    ],
    LegalRelationType.SUPERSEDES: [
        r"thay\s+thế\s+(.+)",
        r"bãi\s+bỏ\s+(.+)",
        r"hết\s+hiệu\s+lực\s+khi\s+(.+)",
    ],
    LegalRelationType.IMPLEMENTS: [
        r"hướng\s+dẫn\s+(?:thi\s+hành\s+)?(.+)",
        r"quy\s+định\s+chi\s+tiết\s+(.+)",
        r"triển\s+khai\s+(.+)",
    ],
    LegalRelationType.AUTHORIZED_BY: [
        r"(.+?)\s+(?:được\s+)?ủy\s+quyền\s+(?:bởi\s+)?(.+)",
        r"(.+?)\s+(?:được\s+)?cho\s+phép\s+(?:bởi\s+)?(.+)",
        r"(.+?)\s+(?:được\s+)?phê\s+duyệt\s+(?:bởi\s+)?(.+)",
    ],
    LegalRelationType.PERFORMED_BY: [
        r"(.+?)\s+(?:do|bởi)\s+(.+?)\s+(?:thực\s+hiện|quyết\s+định)",
        r"(.+?)\s+thuộc\s+(?:thẩm\s+)?quyền\s+(?:của\s+)?(.+)",
        r"(.+?)\s+chịu\s+trách\s+nhiệm\s+(.+)",
    ],
}


# LLM prompt hints for relation extraction (Vietnamese)
RELATION_EXTRACTION_PROMPT_VI = """
Bạn là chuyên gia trích xuất quan hệ từ văn bản pháp luật Việt Nam.

Trích xuất các loại quan hệ sau giữa các thực thể:

1. **REQUIRES** - Điều kiện tiên quyết:
   - "Để thành lập công ty phải có ít nhất 3 cổ đông"
   - "Điều kiện để được cấp phép là..."

2. **HAS_PENALTY** - Hình phạt:
   - "Vi phạm quy định này bị phạt tiền từ 10 đến 20 triệu"
   - "Hành vi X bị xử phạt hành chính"

3. **APPLIES_TO** - Phạm vi áp dụng:
   - "Quy định này áp dụng cho công ty cổ phần"
   - "Điều này áp dụng đối với doanh nghiệp nhà nước"

4. **EXCLUDES** - Loại trừ:
   - "Không áp dụng cho doanh nghiệp nhỏ"
   - "Trừ trường hợp quy định tại Điều 5"

5. **CONDITION_FOR** - Điều kiện:
   - "Nếu có đủ điều kiện thì được cấp phép"
   - "Khi vi phạm thì bị xử lý"

6. **DEFINED_AS** - Định nghĩa:
   - "Doanh nghiệp là tổ chức có tên riêng..."
   - "Vốn điều lệ là tổng giá trị tài sản..."

7. **REFERENCES** - Tham chiếu:
   - "theo quy định tại Điều 5"
   - "căn cứ Khoản 2 Điều 10"

8. **AMENDS** - Sửa đổi:
   - "sửa đổi, bổ sung Điều 15"

9. **SUPERSEDES** - Thay thế:
   - "thay thế Luật Doanh nghiệp 2014"

10. **AUTHORIZED_BY** - Ủy quyền:
    - "được HĐQT ủy quyền"

11. **PERFORMED_BY** - Thực hiện bởi:
    - "do Giám đốc quyết định"

Văn bản cần phân tích:
{text}

Thực thể đã trích xuất:
{entities}

Trả về JSON với format:
[
  {{
    "subject": "HĐQT",
    "predicate": "AUTHORIZED_BY",
    "object": "Đại hội đồng cổ đông",
    "confidence": 0.9,
    "context": "HĐQT được ĐHĐCĐ ủy quyền quyết định..."
  }}
]
"""


# Relation type examples for few-shot learning
RELATION_EXAMPLES: Dict[LegalRelationType, List[str]] = {
    LegalRelationType.REQUIRES: [
        "Để thành lập công ty phải có ít nhất 3 cổ đông",
        "Điều kiện để được cấp phép kinh doanh là phải có vốn điều lệ tối thiểu",
        "Người đại diện theo pháp luật phải có đủ năng lực hành vi dân sự",
    ],
    LegalRelationType.HAS_PENALTY: [
        "Vi phạm quy định này bị phạt tiền từ 10 đến 20 triệu đồng",
        "Hành vi gian lận trong đăng ký doanh nghiệp bị xử phạt hành chính",
        "Công ty không nộp báo cáo tài chính đúng hạn sẽ bị phạt tiền",
    ],
    LegalRelationType.APPLIES_TO: [
        "Quy định này áp dụng cho công ty cổ phần",
        "Điều này không áp dụng đối với doanh nghiệp nhà nước",
        "Luật này áp dụng cho tất cả doanh nghiệp được thành lập tại Việt Nam",
    ],
    LegalRelationType.DEFINED_AS: [
        "Doanh nghiệp là tổ chức có tên riêng, có tài sản",
        "Vốn điều lệ là tổng giá trị tài sản do các thành viên góp",
        "Cổ đông sáng lập là cổ đông sở hữu ít nhất một cổ phần phổ thông",
    ],
    LegalRelationType.REFERENCES: [
        "theo quy định tại Điều 5 Luật này",
        "căn cứ Khoản 2 Điều 10 Nghị định 01/2021/NĐ-CP",
        "quy định tại điểm a khoản 1 Điều 17",
    ],
}


# Inverse relations for bidirectional extraction
INVERSE_RELATIONS: Dict[LegalRelationType, LegalRelationType] = {
    LegalRelationType.REQUIRES: LegalRelationType.CONDITION_FOR,
    LegalRelationType.APPLIES_TO: LegalRelationType.PART_OF,
    LegalRelationType.CONTAINS: LegalRelationType.PART_OF,
    LegalRelationType.AUTHORIZED_BY: LegalRelationType.PERFORMED_BY,
}
