# Agent Workflow

## 1. How the agent chooses a tool
When `AgentRunner` is created, the three tools (name + description + input schema) are given to Gemini through `create_agent`. For every user query Gemini either:
* answers directly (no tool needed), or
* returns an AI message containing `tool_calls` = `[{name, args}]`.

There is **no if/else keyword routing** in our code; the model chooses from the descriptions.

## 2. Step by step
```
1. User Query      "Read the project budget file, calculate the remaining budget"
2. Tool Selection  Gemini -> tool_call read_file {"filename": "project_budget.txt"}
3. Action          LangChain runs our read_file function
4. Observation     file text returned as a ToolMessage (labelled untrusted data)
5. Next Action     Gemini reads it -> tool_call calculator {"expression": "500000-(...)"}
6. Observation     "... = 140000"
7. Final Answer    Gemini writes the explanation (no tool call -> loop ends)
```
`agent_runner.py` streams these updates (`stream_mode="updates"`) and prints them. Gemini's optional short sentence before a call is shown as "why:". Hidden reasoning is not requested or displayed.

## 3. When does it stop?
1. The model replies without a tool call (normal finish), **or**
2. `MAX_MODEL_CALLS` (default 8) is reached - run ends with a limit message, **or**
3. `MAX_TOOL_CALLS` (default 8) is reached - extra tool calls are refused with an error the model can read, **or**
4. An exception occurs - friendly error shown, API key scrubbed, program keeps running.
An empty/malformed model reply is reported as "did not return a usable answer".

## 4. Handling failures
Tools return messages like `File reader error: ...` or `Web search error: ...`. The model sees these as observations and, per the system prompt, must say it could not get the information instead of guessing.

## 5. Safety in the loop
* Tool outputs are data, not instructions (prompt + labels).
* Tools cannot write, run code, or reach outside `sample_files/`.
* Calls to unknown tools are rejected by LangChain without crashing.
