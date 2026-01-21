"""
Legal domain relation types for Vietnamese legal document relation extraction.

Relation types designed for:
- Vietnamese legal documents (Luật, Nghị định, Thông tư)
- Cross-reference relationships between articles
- Semantic relationships in corporate law

These relation types are used by LegalRelationExtractor for extracting
domain-specific relations from legal text.

Includes:
- Generic relations: YÊU_CẦU, BỊ_PHẠT, ÁP_DỤNG_CHO, etc.
- Domain-specific relations: CÓ_QUYỀN, CÓ_NGHĨA_VỤ, CÓ_THẨM_QUYỀN, etc.
- Enum-based types for structured extraction
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


# =============================================================================
# GENERIC RELATION TYPES (Vietnamese)
# =============================================================================
LEGAL_RELATION_TYPES_GENERIC = [
    "YÊU_CẦU",        # X yêu cầu Y (điều kiện tiên quyết)
    "BỊ_PHẠT",        # Vi phạm X bị phạt Y
    "ÁP_DỤNG_CHO",    # Quy định X áp dụng cho Y
    "ĐIỀU_KIỆN_CHO",  # X là điều kiện cho Y
    "ĐỊNH_NGHĨA_LÀ",  # X được định nghĩa là Y
    "THAM_CHIẾU",     # Điều X tham chiếu Điều Y (from Phase 03 cross-refs)
    "SỬA_ĐỔI",        # Điều X sửa đổi Điều Y
    "BAO_GỒM",        # X chứa Y (document → chapter → article)
    "QUY_ĐỊNH_VỀ",    # Nghị định/Luật quy định về X
    "BAN_HÀNH",       # Cơ quan X ban hành văn bản Y
]

# =============================================================================
# DOMAIN-SPECIFIC RELATION TYPES (Legal-specific)
# =============================================================================
LEGAL_RELATION_TYPES_DOMAIN = [
    "CÓ_QUYỀN",           # Chủ thể có quyền thực hiện hành vi (has-right-to)
    "CÓ_NGHĨA_VỤ",        # Chủ thể có nghĩa vụ thực hiện hành vi (has-obligation-to)
    "CÓ_THẨM_QUYỀN",      # Cơ quan có thẩm quyền về X (has-authority)
    "CHỊU_TRÁCH_NHIỆM",   # Chủ thể chịu trách nhiệm về X
    "VI_PHẠM",            # Hành vi vi phạm quy định (violates)
    "CÓ_CHẾ_TÀI",         # Quy định có chế tài X (has-sanction)
    "LOẠI_TRỪ",           # X và Y loại trừ lẫn nhau (excludes)
    "NGOẠI_LỆ_CỦA",       # X là ngoại lệ của quy định Y (exception-to)
    "BẢO_HỘ",             # Nhà nước bảo hộ X
    "NGHIÊM_CẤM",         # Cấm hành vi X
]

# Combined relation types (Vietnamese)
LEGAL_RELATION_TYPES = LEGAL_RELATION_TYPES_GENERIC + LEGAL_RELATION_TYPES_DOMAIN

# Set of defined relation types for O(1) lookup
LEGAL_RELATION_TYPES_SET = frozenset(t.upper() for t in LEGAL_RELATION_TYPES)


# =============================================================================
# TRIGGER WORDS for each relation type (used in prompts)
# =============================================================================
LEGAL_RELATION_TRIGGERS = {
    # Generic relations
    "YÊU_CẦU": ["phải có", "cần có", "yêu cầu", "đòi hỏi", "bắt buộc phải"],
    "BỊ_PHẠT": ["bị phạt", "bị xử phạt", "chịu phạt", "bị xử lý"],
    "ÁP_DỤNG_CHO": ["áp dụng cho", "áp dụng đối với", "được áp dụng"],
    "ĐIỀU_KIỆN_CHO": ["là điều kiện", "với điều kiện", "điều kiện để"],
    "ĐỊNH_NGHĨA_LÀ": ["là", "được hiểu là", "được định nghĩa là", "có nghĩa là"],
    "THAM_CHIẾU": ["theo", "căn cứ", "quy định tại", "nêu tại", "theo quy định"],
    "SỬA_ĐỔI": ["sửa đổi", "bổ sung", "thay thế", "bãi bỏ"],
    "BAO_GỒM": ["bao gồm", "gồm có", "chứa", "bao hàm"],
    "QUY_ĐỊNH_VỀ": ["quy định về", "quy định chi tiết về", "hướng dẫn về"],
    "BAN_HÀNH": ["ban hành", "công bố", "phát hành"],
    # Domain-specific relations
    "CÓ_QUYỀN": ["có quyền", "được quyền", "quyền của", "được phép", "có thể"],
    "CÓ_NGHĨA_VỤ": ["có nghĩa vụ", "phải", "bắt buộc", "có trách nhiệm"],
    "CÓ_THẨM_QUYỀN": ["có thẩm quyền", "thuộc thẩm quyền", "quyết định về", "thẩm quyền của"],
    "CHỊU_TRÁCH_NHIỆM": ["chịu trách nhiệm", "trách nhiệm của", "phải chịu"],
    "VI_PHẠM": ["vi phạm", "không tuân thủ", "trái với", "không thực hiện"],
    "CÓ_CHẾ_TÀI": ["bị xử phạt", "chế tài", "hình phạt", "biện pháp xử lý"],
    "LOẠI_TRỪ": ["loại trừ", "không bao gồm", "trừ", "ngoại trừ"],
    "NGOẠI_LỆ_CỦA": ["trừ trường hợp", "không áp dụng", "ngoại lệ", "trừ khi"],
    "BẢO_HỘ": ["bảo hộ", "bảo vệ", "được bảo hộ"],
    "NGHIÊM_CẤM": ["nghiêm cấm", "cấm", "không được", "không được phép"],
}


# Vietnamese patterns for relation detection (enum-based)
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


# =============================================================================
# VIETNAMESE PROMPT FOR LLM-BASED RELATION EXTRACTION (with trigger words)
# =============================================================================
LEGAL_RELATION_PROMPT_VI = """Bạn là chuyên gia trích xuất quan hệ ngữ nghĩa từ văn bản pháp luật Việt Nam.

Cho các thực thể đã được trích xuất, hãy xác định quan hệ giữa chúng.

## PHẦN 1: QUAN HỆ CHUNG

| Quan hệ | Ý nghĩa | Trigger words |
|---------|---------|---------------|
| YÊU_CẦU | X yêu cầu/cần có Y | "phải có", "cần có", "yêu cầu", "đòi hỏi" |
| BỊ_PHẠT | Vi phạm X bị xử phạt Y | "bị phạt", "bị xử phạt", "chịu phạt" |
| ÁP_DỤNG_CHO | Quy định X áp dụng cho Y | "áp dụng cho", "áp dụng đối với" |
| ĐIỀU_KIỆN_CHO | X là điều kiện để Y | "là điều kiện", "với điều kiện" |
| ĐỊNH_NGHĨA_LÀ | X được định nghĩa là Y | "là", "được hiểu là", "có nghĩa là" |
| THAM_CHIẾU | X tham chiếu đến Y | "theo", "căn cứ", "quy định tại" |
| SỬA_ĐỔI | X sửa đổi/bổ sung Y | "sửa đổi", "bổ sung", "thay thế" |
| BAO_GỒM | X bao gồm/chứa Y | "bao gồm", "gồm có", "chứa" |
| QUY_ĐỊNH_VỀ | Văn bản X quy định về Y | "quy định về", "quy định chi tiết" |
| BAN_HÀNH | Cơ quan X ban hành Y | "ban hành", "công bố" |

## PHẦN 2: QUAN HỆ PHÁP LÝ ĐẶC THÙ

| Quan hệ | Ý nghĩa | Trigger words |
|---------|---------|---------------|
| CÓ_QUYỀN | Chủ thể có quyền thực hiện X | "có quyền", "được quyền", "quyền của", "được phép" |
| CÓ_NGHĨA_VỤ | Chủ thể có nghĩa vụ thực hiện X | "có nghĩa vụ", "phải", "bắt buộc", "có trách nhiệm" |
| CÓ_THẨM_QUYỀN | Cơ quan có thẩm quyền về X | "có thẩm quyền", "thuộc thẩm quyền", "quyết định về" |
| CHỊU_TRÁCH_NHIỆM | Chủ thể chịu trách nhiệm về X | "chịu trách nhiệm", "trách nhiệm của" |
| VI_PHẠM | Hành vi vi phạm quy định X | "vi phạm", "không tuân thủ", "trái với" |
| CÓ_CHẾ_TÀI | Quy định X có chế tài Y | "bị xử phạt", "chế tài", "hình phạt" |
| LOẠI_TRỪ | X loại trừ Y | "loại trừ", "không bao gồm", "trừ" |
| NGOẠI_LỆ_CỦA | X là ngoại lệ của Y | "trừ trường hợp", "không áp dụng", "ngoại lệ" |
| BẢO_HỘ | Nhà nước bảo hộ X | "bảo hộ", "bảo vệ", "được bảo hộ" |
| NGHIÊM_CẤM | Cấm hành vi X | "nghiêm cấm", "cấm", "không được" |

## VÍ DỤ

Văn bản: "Công ty TNHH phải có ít nhất 2 thành viên và được Nhà nước bảo hộ"
Entities: ["Công ty TNHH", "ít nhất 2 thành viên", "Nhà nước"]
→ Relations:
- Công ty TNHH YÊU_CẦU ít nhất 2 thành viên (trigger: "phải có")
- Nhà nước BẢO_HỘ Công ty TNHH (trigger: "được bảo hộ")

**QUAN TRỌNG**:
- Sử dụng CHÍNH XÁC text entity từ danh sách
- Xác định relation dựa trên trigger words trong văn bản

Thực thể đã trích xuất:
{entities}

Văn bản:
{text}

Trả về JSON array với format:
[{{"subject": "entity_text", "predicate": "LOẠI_QUAN_HỆ", "object": "entity_text", "confidence": 0.0-1.0}}]
"""


# =============================================================================
# VIETNAMESE PROMPT FOR FREE RELATION EXTRACTION (no predefined types)
# =============================================================================
LEGAL_RELATION_FREE_PROMPT_VI = """Bạn là chuyên gia trích xuất quan hệ ngữ nghĩa từ văn bản pháp luật Việt Nam.

Cho các thực thể đã được trích xuất từ văn bản pháp luật, hãy xác định TẤT CẢ các quan hệ có ý nghĩa giữa chúng.

**QUAN TRỌNG**: Trong các trường "subject" và "object", bạn PHẢI sử dụng CHÍNH XÁC text của thực thể đã cho trong danh sách. KHÔNG được viết tắt, thêm bớt từ, hay paraphrase.

## HƯỚNG DẪN XÁC ĐỊNH QUAN HỆ

### Quan hệ chung (Generic):
| Trigger words | → Relation type |
|---------------|-----------------|
| "phải có", "cần có", "yêu cầu" | YÊU_CẦU |
| "bị phạt", "bị xử phạt" | BỊ_PHẠT |
| "áp dụng cho", "áp dụng đối với" | ÁP_DỤNG_CHO |
| "là", "được hiểu là", "được định nghĩa là" | ĐỊNH_NGHĨA_LÀ |
| "theo", "căn cứ", "quy định tại" | THAM_CHIẾU |
| "sửa đổi", "bổ sung", "thay thế" | SỬA_ĐỔI |
| "bao gồm", "gồm có", "chứa" | BAO_GỒM |
| "quy định về", "quy định chi tiết" | QUY_ĐỊNH_VỀ |
| "ban hành", "công bố" | BAN_HÀNH |

### Quan hệ pháp lý đặc thù (Domain-specific):
| Trigger words | → Relation type |
|---------------|-----------------|
| "có quyền", "được quyền", "quyền của" | CÓ_QUYỀN |
| "có nghĩa vụ", "phải", "bắt buộc" | CÓ_NGHĨA_VỤ |
| "có thẩm quyền", "thuộc thẩm quyền" | CÓ_THẨM_QUYỀN |
| "chịu trách nhiệm", "trách nhiệm của" | CHỊU_TRÁCH_NHIỆM |
| "vi phạm", "không tuân thủ" | VI_PHẠM |
| "chế tài", "bị xử phạt" | CÓ_CHẾ_TÀI |
| "loại trừ", "không bao gồm", "trừ" | LOẠI_TRỪ |
| "trừ trường hợp", "ngoại lệ" | NGOẠI_LỆ_CỦA |
| "bảo hộ", "bảo vệ" | BẢO_HỘ |
| "nghiêm cấm", "cấm", "không được" | NGHIÊM_CẤM |

Thực thể đã trích xuất (CHỈ sử dụng text trong danh sách này):
{entities}

Văn bản:
{text}

Trả về JSON array với format (đặt tên quan hệ bằng TIẾNG VIỆT, dùng dấu gạch dưới thay khoảng trắng):
[{{"subject": "COPY_CHÍNH_XÁC_TEXT_ENTITY", "predicate": "LOẠI_QUAN_HỆ", "object": "COPY_CHÍNH_XÁC_TEXT_ENTITY", "confidence": 0.0-1.0}}]

Ví dụ với entities: ["Công ty TNHH", "ít nhất 2 thành viên", "Doanh nghiệp", "tổ chức có tên riêng", "Nhà nước"]:
[
  {{"subject": "Công ty TNHH", "predicate": "YÊU_CẦU", "object": "ít nhất 2 thành viên", "confidence": 0.9}},
  {{"subject": "Doanh nghiệp", "predicate": "ĐỊNH_NGHĨA_LÀ", "object": "tổ chức có tên riêng", "confidence": 0.85}},
  {{"subject": "Nhà nước", "predicate": "BẢO_HỘ", "object": "Doanh nghiệp", "confidence": 0.9}}
]
"""


# =============================================================================
# VIETNAMESE COT PROMPT FOR RELATION EXTRACTION (Chain-of-Thought)
# =============================================================================
LEGAL_RELATION_COT_PROMPT_VI = """Bạn là chuyên gia trích xuất quan hệ ngữ nghĩa từ văn bản pháp luật Việt Nam.

**RÀNG BUỘC QUAN TRỌNG NHẤT:**
- Subject và Object PHẢI là 2 thực thể KHÁC NHAU
- Quan hệ mà subject = object là KHÔNG HỢP LỆ → KHÔNG được trích xuất
- Loại quan hệ PHẢI viết HOA (VD: CÓ_QUYỀN, không phải có_quyền)

## BƯỚC 1: Xác định thực thể
Liệt kê các thực thể trong văn bản và vai trò của chúng:
- Chủ thể (ORG, PERSON_ROLE): ai/cái gì thực hiện hành động?
- Đối tượng (LEGAL_TERM, ACTION): hành động/thuộc tính gì?

## BƯỚC 2: Phân tích ngữ cảnh
Với mỗi cặp thực thể KHÁC NHAU, xác định:
- Có trigger word không? (phải, có quyền, được phép, bị cấm...)
- Có phủ định không? ("không được" = NGHIÊM_CẤM, không phải CÓ_QUYỀN)

## BƯỚC 3: Xác định loại quan hệ
Chọn loại quan hệ từ danh sách (PHẢI viết HOA):

| Trigger words | → Relation type |
|---------------|-----------------|
| "phải có", "cần có", "yêu cầu" | YÊU_CẦU |
| "bị phạt", "bị xử phạt" | BỊ_PHẠT |
| "áp dụng cho", "áp dụng đối với" | ÁP_DỤNG_CHO |
| "là", "được hiểu là", "được định nghĩa là" | ĐỊNH_NGHĨA_LÀ |
| "theo", "căn cứ", "quy định tại" | THAM_CHIẾU |
| "bao gồm", "gồm có", "chứa" | BAO_GỒM |
| "có quyền", "được quyền", "được phép" | CÓ_QUYỀN |
| "có nghĩa vụ", "phải", "bắt buộc" | CÓ_NGHĨA_VỤ |
| "chịu trách nhiệm", "trách nhiệm của" | CHỊU_TRÁCH_NHIỆM |
| "nghiêm cấm", "cấm", "không được" | NGHIÊM_CẤM |

## BƯỚC 4: Kiểm tra hợp lệ (BẮT BUỘC)
Với mỗi quan hệ, kiểm tra:
✓ Subject và Object là 2 thực thể KHÁC NHAU?
✓ Loại quan hệ viết HOA đúng cách?
✓ Subject/Object copy CHÍNH XÁC từ danh sách entities?

---

## VÍ DỤ ĐÚNG:

**Văn bản:** "Công ty cổ phần phải có Hội đồng quản trị. HĐQT có quyền quyết định chiến lược phát triển."
**Entities:** ["Công ty cổ phần", "Hội đồng quản trị", "HĐQT", "chiến lược phát triển"]

**Phân tích:**
1. "phải có" giữa "Công ty cổ phần" và "Hội đồng quản trị" → YÊU_CẦU
2. "có quyền" giữa "HĐQT" và "chiến lược phát triển" → CÓ_QUYỀN

**Kết quả:**
[
  {{"subject": "Công ty cổ phần", "predicate": "YÊU_CẦU", "object": "Hội đồng quản trị", "confidence": 0.95}},
  {{"subject": "HĐQT", "predicate": "CÓ_QUYỀN", "object": "chiến lược phát triển", "confidence": 0.9}}
]

---

**Văn bản:** "Doanh nghiệp là tổ chức có tên riêng, có tài sản, có trụ sở giao dịch."
**Entities:** ["Doanh nghiệp", "tổ chức có tên riêng", "tài sản", "trụ sở giao dịch"]

**Phân tích:**
1. "là" giữa "Doanh nghiệp" và "tổ chức có tên riêng" → ĐỊNH_NGHĨA_LÀ
2. "có" giữa "Doanh nghiệp" và "tài sản" → YÊU_CẦU (ownership requirement)
3. "có" giữa "Doanh nghiệp" và "trụ sở giao dịch" → YÊU_CẦU

**Kết quả:**
[
  {{"subject": "Doanh nghiệp", "predicate": "ĐỊNH_NGHĨA_LÀ", "object": "tổ chức có tên riêng", "confidence": 0.95}},
  {{"subject": "Doanh nghiệp", "predicate": "YÊU_CẦU", "object": "tài sản", "confidence": 0.85}},
  {{"subject": "Doanh nghiệp", "predicate": "YÊU_CẦU", "object": "trụ sở giao dịch", "confidence": 0.85}}
]

---

**Văn bản:** "Giám đốc chịu trách nhiệm về hoạt động kinh doanh. Giám đốc có quyền tuyển dụng lao động."
**Entities:** ["Giám đốc", "hoạt động kinh doanh", "tuyển dụng lao động"]

**Phân tích:**
1. "chịu trách nhiệm về" giữa "Giám đốc" và "hoạt động kinh doanh" → CHỊU_TRÁCH_NHIỆM
2. "có quyền" giữa "Giám đốc" và "tuyển dụng lao động" → CÓ_QUYỀN

**Kết quả:**
[
  {{"subject": "Giám đốc", "predicate": "CHỊU_TRÁCH_NHIỆM", "object": "hoạt động kinh doanh", "confidence": 0.95}},
  {{"subject": "Giám đốc", "predicate": "CÓ_QUYỀN", "object": "tuyển dụng lao động", "confidence": 0.9}}
]

---

**Văn bản:** "Thành viên không được rút vốn đã góp ra khỏi công ty dưới mọi hình thức."
**Entities:** ["Thành viên", "rút vốn đã góp", "công ty"]

**Phân tích:**
1. "không được" là phủ định → NGHIÊM_CẤM (không phải CÓ_QUYỀN!)
2. Subject: "Thành viên", Object: "rút vốn đã góp"

**Kết quả:**
[
  {{"subject": "Thành viên", "predicate": "NGHIÊM_CẤM", "object": "rút vốn đã góp", "confidence": 0.95}}
]

---

**Văn bản:** "Điều 24 quy định về điều kiện đối với Giám đốc theo quy định tại Điều 64 Luật này."
**Entities:** ["Điều 24", "điều kiện đối với Giám đốc", "Điều 64"]

**Phân tích:**
1. "quy định về" giữa "Điều 24" và "điều kiện đối với Giám đốc" → QUY_ĐỊNH_VỀ
2. "theo quy định tại" giữa "Điều 24" và "Điều 64" → THAM_CHIẾU

**Kết quả:**
[
  {{"subject": "Điều 24", "predicate": "QUY_ĐỊNH_VỀ", "object": "điều kiện đối với Giám đốc", "confidence": 0.9}},
  {{"subject": "Điều 24", "predicate": "THAM_CHIẾU", "object": "Điều 64", "confidence": 0.95}}
]

---

## VÍ DỤ SAI (KHÔNG ĐƯỢC LÀM):

❌ SAI - Self-reference:
{{"subject": "Đăng ký doanh nghiệp", "predicate": "BAO_GỒM", "object": "Đăng ký doanh nghiệp"}}
→ Subject = Object là KHÔNG HỢP LỆ!

❌ SAI - Bỏ lỡ phủ định:
Văn bản: "Thành viên không được rút vốn"
{{"subject": "Thành viên", "predicate": "CÓ_QUYỀN", "object": "rút vốn"}}
→ PHẢI là NGHIÊM_CẤM vì có "không được"!

❌ SAI - Lowercase predicate:
{{"subject": "Công ty", "predicate": "có_quyền", "object": "kinh doanh"}}
→ PHẢI viết HOA: "CÓ_QUYỀN"

---

Thực thể đã trích xuất (CHỈ sử dụng text trong danh sách này):
{entities}

Văn bản:
{text}

**BƯỚC CUỐI: Tự kiểm tra trước khi trả lời:**
1. Có quan hệ nào subject = object không? → Loại bỏ!
2. Tất cả predicate đã viết HOA chưa?
3. Subject/Object có copy chính xác từ entities không?

Trả về JSON array:
[{{"subject": "ENTITY_TEXT", "predicate": "LOẠI_QUAN_HỆ_VIẾT_HOA", "object": "ENTITY_TEXT_KHÁC", "confidence": 0.0-1.0}}]
"""


# =============================================================================
# RELATION PATTERNS FOR PATTERN-BASED EXTRACTION FALLBACK
# =============================================================================
LEGAL_RELATION_PATTERNS = {
    # Generic relations
    "YÊU_CẦU": [
        r"(?P<subject>.+?)\s+(?:phải có|cần có|yêu cầu|đòi hỏi)\s+(?P<object>.+)",
        r"(?:Để|Muốn)\s+(?P<subject>.+?)\s+(?:phải|cần)\s+(?P<object>.+)",
        r"(?P<subject>.+?)\s+là điều kiện (?:tiên quyết |bắt buộc )?(?:để|cho)\s+(?P<object>.+)",
    ],
    "BỊ_PHẠT": [
        r"(?:Vi phạm|Không tuân thủ)\s+(?P<subject>.+?)\s+(?:bị phạt|bị xử phạt)\s+(?P<object>.+)",
        r"(?P<subject>.+?)\s+(?:bị phạt tiền|bị xử phạt hành chính)\s+(?P<object>.+)",
    ],
    "ÁP_DỤNG_CHO": [
        r"(?P<subject>.+?)\s+(?:áp dụng cho|áp dụng đối với)\s+(?P<object>.+)",
        r"(?:Quy định này|Điều này)\s+(?:áp dụng cho|áp dụng đối với)\s+(?P<object>.+)",
    ],
    "ĐỊNH_NGHĨA_LÀ": [
        r"(?P<subject>.+?)\s+(?:là|được hiểu là|được định nghĩa là)\s+(?P<object>.+)",
        r"(?P<subject>.+?)\s+(?:có nghĩa là)\s+(?P<object>.+)",
    ],
    "THAM_CHIẾU": [
        r"(?:theo|căn cứ|quy định tại)\s+(?P<object>(?:Điều|Khoản|Điểm)\s+\d+)",
        r"(?:như|nêu tại)\s+(?P<object>(?:Điều|Khoản)\s+\d+)",
    ],
    "BAO_GỒM": [
        r"(?P<subject>.+?)\s+(?:bao gồm|gồm có|chứa)\s+(?P<object>.+)",
    ],
    "QUY_ĐỊNH_VỀ": [
        r"(?P<subject>.+?)\s+(?:quy định về|quy định chi tiết về)\s+(?P<object>.+)",
    ],
    "BAN_HÀNH": [
        r"(?P<subject>.+?)\s+(?:ban hành|công bố)\s+(?P<object>.+)",
    ],
    # Domain-specific relations
    "CÓ_QUYỀN": [
        r"(?P<subject>.+?)\s+(?:có quyền|được quyền|được phép)\s+(?P<object>.+)",
        r"(?:Quyền của)\s+(?P<subject>.+?)\s+(?:là|gồm|bao gồm)\s+(?P<object>.+)",
    ],
    "CÓ_NGHĨA_VỤ": [
        r"(?P<subject>.+?)\s+(?:có nghĩa vụ|có trách nhiệm)\s+(?P<object>.+)",
        r"(?P<subject>.+?)\s+(?:phải|bắt buộc)\s+(?P<object>.+)",
    ],
    "CÓ_THẨM_QUYỀN": [
        r"(?P<subject>.+?)\s+(?:có thẩm quyền|thuộc thẩm quyền)\s+(?P<object>.+)",
        r"(?:Thẩm quyền của)\s+(?P<subject>.+?)\s+(?:là|gồm)\s+(?P<object>.+)",
    ],
    "CHỊU_TRÁCH_NHIỆM": [
        r"(?P<subject>.+?)\s+(?:chịu trách nhiệm về|chịu trách nhiệm)\s+(?P<object>.+)",
    ],
    "VI_PHẠM": [
        r"(?P<subject>.+?)\s+(?:vi phạm|không tuân thủ|trái với)\s+(?P<object>.+)",
    ],
    "BẢO_HỘ": [
        r"(?P<subject>.+?)\s+(?:bảo hộ|bảo vệ)\s+(?P<object>.+)",
        r"(?P<object>.+?)\s+(?:được\s+)?(?P<subject>.+?)\s+bảo hộ",
    ],
    "NGHIÊM_CẤM": [
        r"(?:Nghiêm cấm|Cấm)\s+(?P<subject>.+?)\s+(?P<object>.+)",
        r"(?P<subject>.+?)\s+(?:không được|không được phép)\s+(?P<object>.+)",
    ],
    "LOẠI_TRỪ": [
        r"(?P<subject>.+?)\s+(?:loại trừ|không bao gồm)\s+(?P<object>.+)",
        r"(?P<subject>.+?)\s+(?:trừ)\s+(?P<object>.+)",
    ],
    "NGOẠI_LỆ_CỦA": [
        r"(?:Trừ trường hợp|Ngoại lệ)\s+(?P<object>.+?),?\s+(?P<subject>.+)",
    ],
}
