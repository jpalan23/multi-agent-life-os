from core.llm_factory import get_llm

try:
    print("Testing LLM Factory instantiation...")
    llm = get_llm()
    print(f"Successfully instantiated: {type(llm).__name__}")
    print(f"Model configured: {llm.model}")
    print("Factory is ready!")
except Exception as e:
    print(f"Error during instantiation: {e}")
