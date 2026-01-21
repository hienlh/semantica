"""
Legal relation types for RelationExtractor config.

These types are used by Semantica RelationExtractor to focus extraction
on relations relevant to Vietnamese legal documents.

Includes:
- Generic relations: YÊU_CẦU, BỊ_PHẠT, ÁP_DỤNG_CHO, etc.
- Domain-specific relations: CÓ_QUYỀN, CÓ_NGHĨA_VỤ, CÓ_THẨM_QUYỀN, etc.
"""

# =============================================================================
# GENERIC RELATION TYPES
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

# Combined relation types (for backward compatibility)
LEGAL_RELATION_TYPES = LEGAL_RELATION_TYPES_GENERIC + LEGAL_RELATION_TYPES_DOMAIN

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
