"""
Legal Ontology Generator for Vietnamese legal documents.

Generates OWL ontology from knowledge graph with:
- Class hierarchy for legal entities
- Object properties for relations
- Data properties for attributes
- Validation using reasoner

Designed for Vietnamese legal domain with corporate law focus.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ..utils.logging import get_logger

from .entity_types import LegalEntityType
from .kg_builder import LegalKnowledgeGraph, KGNode, KGEdge
from .relation_types import LegalRelationType


@dataclass
class OntologyClass:
    """OWL class definition."""

    name: str
    label: str
    parent: Optional[str] = None
    description: str = ""
    properties: List[str] = field(default_factory=list)


@dataclass
class OntologyProperty:
    """OWL property definition."""

    name: str
    label: str
    property_type: str  # "ObjectProperty" or "DataProperty"
    domain: str
    range: str
    description: str = ""


@dataclass
class LegalOntology:
    """Legal domain ontology container."""

    classes: Dict[str, OntologyClass] = field(default_factory=dict)
    properties: Dict[str, OntologyProperty] = field(default_factory=dict)
    base_uri: str = "https://semantica.dev/legal/ontology#"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_class(self, cls: OntologyClass) -> None:
        """Add an ontology class."""
        self.classes[cls.name] = cls

    def add_property(self, prop: OntologyProperty) -> None:
        """Add an ontology property."""
        self.properties[prop.name] = prop

    def to_turtle(self) -> str:
        """Export ontology to Turtle format."""
        lines = [
            f"@prefix : <{self.base_uri}> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "",
            "# Ontology declaration",
            f"<{self.base_uri}> a owl:Ontology ;",
            '    rdfs:label "Vietnamese Legal Document Ontology" ;',
            '    rdfs:comment "Ontology for Vietnamese legal documents (Luật, Nghị định, Thông tư)" .',
            "",
        ]

        # Classes
        lines.append("# Classes")
        for cls in self.classes.values():
            lines.append(f":{cls.name} a owl:Class ;")
            lines.append(f'    rdfs:label "{cls.label}"@vi ;')
            if cls.parent:
                lines.append(f"    rdfs:subClassOf :{cls.parent} ;")
            if cls.description:
                lines.append(f'    rdfs:comment "{cls.description}"@vi ;')
            lines[-1] = lines[-1].rstrip(" ;") + " ."
            lines.append("")

        # Object Properties
        lines.append("# Object Properties")
        for prop in self.properties.values():
            if prop.property_type == "ObjectProperty":
                lines.append(f":{prop.name} a owl:ObjectProperty ;")
                lines.append(f'    rdfs:label "{prop.label}"@vi ;')
                lines.append(f"    rdfs:domain :{prop.domain} ;")
                lines.append(f"    rdfs:range :{prop.range} ;")
                if prop.description:
                    lines.append(f'    rdfs:comment "{prop.description}"@vi ;')
                lines[-1] = lines[-1].rstrip(" ;") + " ."
                lines.append("")

        # Data Properties
        lines.append("# Data Properties")
        for prop in self.properties.values():
            if prop.property_type == "DataProperty":
                lines.append(f":{prop.name} a owl:DatatypeProperty ;")
                lines.append(f'    rdfs:label "{prop.label}"@vi ;')
                lines.append(f"    rdfs:domain :{prop.domain} ;")
                lines.append(f"    rdfs:range {prop.range} ;")
                if prop.description:
                    lines.append(f'    rdfs:comment "{prop.description}"@vi ;')
                lines[-1] = lines[-1].rstrip(" ;") + " ."
                lines.append("")

        return "\n".join(lines)


# Predefined legal domain class hierarchy
LEGAL_CLASS_HIERARCHY = {
    "Thing": None,
    # Top-level legal classes
    "LegalEntity": "Thing",
    "LegalDocument": "Thing",
    "LegalConcept": "Thing",
    "LegalActor": "Thing",
    # Organization hierarchy
    "Organization": "LegalEntity",
    "Company": "Organization",
    "JointStockCompany": "Company",
    "LimitedLiabilityCompany": "Company",
    "PrivateEnterprise": "Company",
    "StateOwnedEnterprise": "Company",
    "Cooperative": "Organization",
    "Branch": "Organization",
    "RepresentativeOffice": "Organization",
    # Person/Role hierarchy
    "PersonRole": "LegalActor",
    "Director": "PersonRole",
    "GeneralDirector": "Director",
    "ChairPerson": "PersonRole",
    "BoardMember": "PersonRole",
    "Shareholder": "PersonRole",
    "FoundingShareholder": "Shareholder",
    "LegalRepresentative": "PersonRole",
    "Controller": "PersonRole",
    "Accountant": "PersonRole",
    # Legal Document hierarchy
    "Law": "LegalDocument",
    "Decree": "LegalDocument",
    "Circular": "LegalDocument",
    "Decision": "LegalDocument",
    "Resolution": "LegalDocument",
    # Legal Concept hierarchy
    "LegalTerm": "LegalConcept",
    "CharterCapital": "LegalTerm",
    "Share": "LegalTerm",
    "CommonShare": "Share",
    "PreferredShare": "Share",
    "ContributedCapital": "LegalTerm",
    "Charter": "LegalTerm",
    "Contract": "LegalTerm",
    "Right": "LegalTerm",
    "Obligation": "LegalTerm",
    # Quantity hierarchy
    "Quantity": "LegalConcept",
    "MonetaryAmount": "Quantity",
    "Percentage": "Quantity",
    "Duration": "Quantity",
    # Penalty hierarchy
    "Penalty": "LegalConcept",
    "Fine": "Penalty",
    "Suspension": "Penalty",
    "Revocation": "Penalty",
    "Ban": "Penalty",
}

# Vietnamese labels for classes
LEGAL_CLASS_LABELS_VI = {
    "Thing": "Sự vật",
    "LegalEntity": "Chủ thể pháp lý",
    "LegalDocument": "Văn bản pháp luật",
    "LegalConcept": "Khái niệm pháp lý",
    "LegalActor": "Chủ thể hành động",
    "Organization": "Tổ chức",
    "Company": "Công ty",
    "JointStockCompany": "Công ty cổ phần",
    "LimitedLiabilityCompany": "Công ty TNHH",
    "PrivateEnterprise": "Doanh nghiệp tư nhân",
    "StateOwnedEnterprise": "Doanh nghiệp nhà nước",
    "Cooperative": "Hợp tác xã",
    "Branch": "Chi nhánh",
    "RepresentativeOffice": "Văn phòng đại diện",
    "PersonRole": "Chức vụ",
    "Director": "Giám đốc",
    "GeneralDirector": "Tổng giám đốc",
    "ChairPerson": "Chủ tịch",
    "BoardMember": "Thành viên Hội đồng",
    "Shareholder": "Cổ đông",
    "FoundingShareholder": "Cổ đông sáng lập",
    "LegalRepresentative": "Người đại diện theo pháp luật",
    "Controller": "Kiểm soát viên",
    "Accountant": "Kế toán trưởng",
    "Law": "Luật",
    "Decree": "Nghị định",
    "Circular": "Thông tư",
    "Decision": "Quyết định",
    "Resolution": "Nghị quyết",
    "LegalTerm": "Thuật ngữ pháp lý",
    "CharterCapital": "Vốn điều lệ",
    "Share": "Cổ phần",
    "CommonShare": "Cổ phần phổ thông",
    "PreferredShare": "Cổ phần ưu đãi",
    "ContributedCapital": "Phần vốn góp",
    "Charter": "Điều lệ",
    "Contract": "Hợp đồng",
    "Right": "Quyền",
    "Obligation": "Nghĩa vụ",
    "Quantity": "Số lượng",
    "MonetaryAmount": "Số tiền",
    "Percentage": "Tỷ lệ phần trăm",
    "Duration": "Thời hạn",
    "Penalty": "Hình phạt",
    "Fine": "Phạt tiền",
    "Suspension": "Đình chỉ",
    "Revocation": "Thu hồi",
    "Ban": "Cấm",
}

# Mapping from entity types to ontology classes
ENTITY_TYPE_TO_CLASS = {
    LegalEntityType.ORGANIZATION: "Organization",
    LegalEntityType.PERSON_ROLE: "PersonRole",
    LegalEntityType.LEGAL_TERM: "LegalTerm",
    LegalEntityType.MONETARY: "MonetaryAmount",
    LegalEntityType.PERCENTAGE: "Percentage",
    LegalEntityType.DURATION: "Duration",
    LegalEntityType.CONDITION: "LegalConcept",
    LegalEntityType.ACTION: "LegalConcept",
    LegalEntityType.PENALTY: "Penalty",
}

# Mapping from relation types to ontology properties
RELATION_TYPE_TO_PROPERTY = {
    LegalRelationType.REQUIRES: ("requires", "yêu cầu"),
    LegalRelationType.DEPENDS_ON: ("dependsOn", "phụ thuộc vào"),
    LegalRelationType.HAS_PENALTY: ("hasPenalty", "có hình phạt"),
    LegalRelationType.RESULTS_IN: ("resultsIn", "dẫn đến"),
    LegalRelationType.APPLIES_TO: ("appliesTo", "áp dụng cho"),
    LegalRelationType.EXCLUDES: ("excludes", "loại trừ"),
    LegalRelationType.CONDITION_FOR: ("conditionFor", "điều kiện cho"),
    LegalRelationType.DEFINED_AS: ("definedAs", "được định nghĩa là"),
    LegalRelationType.INCLUDES: ("includes", "bao gồm"),
    LegalRelationType.REFERENCES: ("references", "tham chiếu đến"),
    LegalRelationType.AMENDS: ("amends", "sửa đổi"),
    LegalRelationType.SUPERSEDES: ("supersedes", "thay thế"),
    LegalRelationType.IMPLEMENTS: ("implements", "hướng dẫn thi hành"),
    LegalRelationType.CONTAINS: ("contains", "chứa"),
    LegalRelationType.PART_OF: ("partOf", "là một phần của"),
    LegalRelationType.AUTHORIZED_BY: ("authorizedBy", "được ủy quyền bởi"),
    LegalRelationType.PERFORMED_BY: ("performedBy", "thực hiện bởi"),
}


class LegalOntologyGenerator:
    """
    Generate OWL ontology from legal knowledge graph.

    Features:
    - Class inference from entity types
    - Property inference from relations
    - Hierarchy generation
    - Turtle/OWL output

    Example:
        >>> generator = LegalOntologyGenerator()
        >>> ontology = generator.generate_from_kg(kg)
        >>> turtle = ontology.to_turtle()
        >>> with open("legal_ontology.ttl", "w") as f:
        ...     f.write(turtle)
    """

    def __init__(
        self,
        base_uri: str = "https://semantica.dev/legal/ontology#",
        include_hierarchy: bool = True,
        min_occurrences: int = 1,
    ):
        """
        Initialize the Ontology Generator.

        Args:
            base_uri: Base URI for the ontology
            include_hierarchy: Include predefined class hierarchy
            min_occurrences: Minimum entity occurrences to create class
        """
        self.logger = get_logger("legal_ontology_generator")
        self.base_uri = base_uri
        self.include_hierarchy = include_hierarchy
        self.min_occurrences = min_occurrences

    def generate_base_ontology(self) -> LegalOntology:
        """
        Generate base ontology with predefined hierarchy.

        Returns:
            LegalOntology with classes and properties
        """
        ontology = LegalOntology(base_uri=self.base_uri)

        # Add predefined classes
        for class_name, parent in LEGAL_CLASS_HIERARCHY.items():
            label = LEGAL_CLASS_LABELS_VI.get(class_name, class_name)
            cls = OntologyClass(
                name=class_name,
                label=label,
                parent=parent,
            )
            ontology.add_class(cls)

        # Add predefined properties from relation types
        for rel_type, (prop_name, prop_label) in RELATION_TYPE_TO_PROPERTY.items():
            prop = OntologyProperty(
                name=prop_name,
                label=prop_label,
                property_type="ObjectProperty",
                domain="Thing",
                range="Thing",
            )
            ontology.add_property(prop)

        # Add common data properties
        data_properties = [
            ("hasConfidence", "độ tin cậy", "Thing", "xsd:decimal"),
            ("hasText", "nội dung", "Thing", "xsd:string"),
            ("hasSourceId", "ID nguồn", "Thing", "xsd:string"),
            ("validFrom", "hiệu lực từ", "Thing", "xsd:dateTime"),
            ("validUntil", "hiệu lực đến", "Thing", "xsd:dateTime"),
        ]
        for name, label, domain, range_ in data_properties:
            prop = OntologyProperty(
                name=name,
                label=label,
                property_type="DataProperty",
                domain=domain,
                range=range_,
            )
            ontology.add_property(prop)

        return ontology

    def generate_from_kg(
        self,
        kg: LegalKnowledgeGraph,
        include_base: bool = True,
    ) -> LegalOntology:
        """
        Generate ontology from knowledge graph.

        Args:
            kg: Legal knowledge graph
            include_base: Include predefined base ontology

        Returns:
            LegalOntology with inferred classes and properties
        """
        if include_base:
            ontology = self.generate_base_ontology()
        else:
            ontology = LegalOntology(base_uri=self.base_uri)

        # Infer classes from entity types in KG
        entity_type_counts: Dict[LegalEntityType, int] = {}
        for node in kg.nodes.values():
            entity_type_counts[node.entity_type] = (
                entity_type_counts.get(node.entity_type, 0) + 1
            )

        for entity_type, count in entity_type_counts.items():
            if count >= self.min_occurrences:
                class_name = ENTITY_TYPE_TO_CLASS.get(entity_type, entity_type.value)
                if class_name not in ontology.classes:
                    # Add class from entity type
                    label = LEGAL_CLASS_LABELS_VI.get(class_name, entity_type.value)
                    cls = OntologyClass(
                        name=class_name,
                        label=label,
                        parent="Thing",
                    )
                    ontology.add_class(cls)

        # Infer properties from relation types in KG
        relation_type_info: Dict[LegalRelationType, Set[tuple]] = {}
        for edge in kg.edges.values():
            if edge.relation_type not in relation_type_info:
                relation_type_info[edge.relation_type] = set()

            # Get source and target node types
            source_node = kg.get_node(edge.source_id)
            target_node = kg.get_node(edge.target_id)
            if source_node and target_node:
                source_class = ENTITY_TYPE_TO_CLASS.get(
                    source_node.entity_type, "Thing"
                )
                target_class = ENTITY_TYPE_TO_CLASS.get(
                    target_node.entity_type, "Thing"
                )
                relation_type_info[edge.relation_type].add((source_class, target_class))

        # Update property domains/ranges based on actual usage
        for rel_type, domain_range_pairs in relation_type_info.items():
            prop_info = RELATION_TYPE_TO_PROPERTY.get(rel_type)
            if prop_info:
                prop_name, prop_label = prop_info
                if prop_name in ontology.properties:
                    # Get most common domain/range
                    domains = [d for d, r in domain_range_pairs]
                    ranges = [r for d, r in domain_range_pairs]
                    if domains:
                        most_common_domain = max(set(domains), key=domains.count)
                        ontology.properties[prop_name].domain = most_common_domain
                    if ranges:
                        most_common_range = max(set(ranges), key=ranges.count)
                        ontology.properties[prop_name].range = most_common_range

        # Update metadata
        ontology.metadata["generated_from_kg"] = True
        ontology.metadata["num_classes"] = len(ontology.classes)
        ontology.metadata["num_properties"] = len(ontology.properties)
        ontology.metadata["source_nodes"] = len(kg.nodes)
        ontology.metadata["source_edges"] = len(kg.edges)

        return ontology

    def validate_ontology(self, ontology: LegalOntology) -> Dict[str, Any]:
        """
        Validate ontology structure.

        Args:
            ontology: Ontology to validate

        Returns:
            Validation report with issues
        """
        issues = []

        # Check class hierarchy
        for cls in ontology.classes.values():
            if cls.parent and cls.parent not in ontology.classes:
                issues.append({
                    "type": "missing_parent",
                    "class": cls.name,
                    "parent": cls.parent,
                })

        # Check property domains/ranges
        for prop in ontology.properties.values():
            if prop.property_type == "ObjectProperty":
                if prop.domain not in ontology.classes:
                    issues.append({
                        "type": "invalid_domain",
                        "property": prop.name,
                        "domain": prop.domain,
                    })
                if prop.range not in ontology.classes:
                    issues.append({
                        "type": "invalid_range",
                        "property": prop.name,
                        "range": prop.range,
                    })

        # Check for orphan classes
        referenced_parents = {c.parent for c in ontology.classes.values() if c.parent}
        for cls_name in ontology.classes:
            if cls_name != "Thing" and cls_name not in referenced_parents:
                parent = ontology.classes[cls_name].parent
                if not parent:
                    issues.append({
                        "type": "orphan_class",
                        "class": cls_name,
                    })

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "num_classes": len(ontology.classes),
            "num_properties": len(ontology.properties),
        }
