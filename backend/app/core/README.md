# core

`models.py` is the shared contract: brief, source line, mapping, result, tool run, work item, audit row, policy, agent session, edit, and the typed input and output of each agent.
Cayden owns it.
Send change requests to Cayden.
`config.py` reads settings from the environment.
`agreement.py` normalizes the credit agreement text and indexes its sections and definitions, for the Brief Reader's quote checks.
`verifier.py` is the Brief verifier (D23): code that checks every field of a draft Brief against the agreement and reports field by field.
`policies.py` is the one rule for which learned policy covers which line, used by the gateway and the scripted Mapper.
