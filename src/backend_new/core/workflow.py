from enum import Enum, auto

class WorkflowManager:
    class PipelineStage(Enum):
        DOWNLOAD = auto()
        GENIUS = auto()
        STEMS = auto()
        MORPHOLOGICAL = auto()
        TRANSLATE = auto()

    def __init__(self, song_ctx):
        ...