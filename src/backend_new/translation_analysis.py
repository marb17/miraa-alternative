class Translator:
    def __init__(self) -> None:
        # TODO ask use to choose what model
        self._llm = None
        self._pipe = None
        # model save loc
        import os
        from pathlib import Path
        self._script_dir = Path(__file__).resolve().parent
        self._base_dir = self._script_dir.parents[0]
        self._model_dir = Path(self._base_dir / "models/hugging_face")
        os.environ["HF_HOME"] = str(self._model_dir)
        self._model_id = str(self._model_dir / "shisa-v2.1-qwen3-8b-awq")

    # region batched inference
    # TODO trying out batched, maybe add a feature where it monitors GPU usage and changes batch size
    def init_model(self) -> None:
        from lmdeploy import pipeline

        self._pipe = pipeline(self._model_id)

    def batch_inference(self, prompts: list[str]) -> list[str]:
        if self._pipe is None:
            self.init_model()

        return [response.text for response in self._pipe(prompts)]

if __name__ == "__main__":
    llm_model = Translator()
    data = llm_model.batch_inference(["what is your name?", "what languages do you support?"])

    print(data)
