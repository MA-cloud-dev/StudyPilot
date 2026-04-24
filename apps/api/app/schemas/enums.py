from enum import Enum


class BaseStringEnum(str, Enum):
    pass


class WorkflowStage(BaseStringEnum):
    ONBOARDING = "onboarding"
    PLANNING = "planning"
    LEARNING = "learning"
    CHECKPOINT_TEST = "checkpoint_test"
    UNIT_REVIEW = "unit_review"
    UNIT_TEST = "unit_test"
    FINAL_REVIEW = "final_review"
    FINAL_TEST = "final_test"
    NEXT_CYCLE = "next_cycle"


class KnowledgeAssetStatus(BaseStringEnum):
    UPLOADING = "uploading"
    PARSING = "parsing"
    INDEXING = "indexing"
    READY = "ready"
    PARSE_FAILED = "parse_failed"


class ParseErrorReason(BaseStringEnum):
    UNSUPPORTED_FORMAT = "unsupported_format"
    FILE_CORRUPTED = "file_corrupted"
    EMPTY_CONTENT = "empty_content"


class PlanStatus(BaseStringEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"


class AssessmentType(BaseStringEnum):
    CHECKPOINT = "checkpoint"
    UNIT = "unit"
    FINAL = "final"


class AssessmentStatus(BaseStringEnum):
    GENERATED = "generated"
    SUBMITTED = "submitted"
    EVALUATED = "evaluated"
