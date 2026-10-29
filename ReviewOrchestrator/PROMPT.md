here is a list of ai chats with different web tools:
first prompt:
https://chatgpt.com/c/6ae355ca-17a4-83eb-b26b-38244eb1971e
https://claude.ai/chat/09e85d21-ad05-4fe0-b10d-8ef14cc23da7

refined prompt after i saw the thinking output of the first prompt even before there results are in:
https://claude.ai/chat/0a5ff96f-8165-4dec-b69e-0a0723d7d286
https://chatgpt.com/c/6ae356bd-fa4c-83eb-8b2c-5a777b52333a
https://chat.mistral.ai/code/01a18896-7c9a-7259-a8b0-1021401b8abd/01a18897-02b1-723e-8eac-66f06540eb7a
https://gemini.google.com/app/bb0b8f672792cf16
https://github.com/copilot/tasks/b471892c-1453-4af2-92fa-5f94611b2a73
https://github.com/copilot/tasks/1976d0f6-45af-48c0-b323-2ce130b5afeb


Extract the html file from all chats into a folder named {Providername}-{Tool}-{Model}-{Thinkinglevel/Effortlevel}-{Prompt version} using Claude in Chrome. Example for the first chatgpt link: OpenAI-Web-GPT6-Pro-v0
Extract the full chat transcription also into that folder as TRANSCRIPTION.md
Save both prompts into the project root as prompt0.txt and prompt1.txt

When that is done add, commit and push this repo.
then create a folder Review in this folder.
there you create 3 folder:
HTML-Review
TRANSCRIPT-Review
Browser-Review

for each chat that we exported start 3 Opus xhigh Agents:
1. one agent that just looks at the html file we extracted. he delivers a REVIEW.md to Review/HTML-Review/{Providername}-{Tool}-{Model}-{Thinkinglevel/Effortlevel}-{Prompt version}. You save its chat transcript to TRANSCRIPT.md in Review/HTML-Review/{Providername}-{Tool}-{Model}-{Thinkinglevel/Effortlevel}-{Prompt version}. It's prompt gets saved to Review/HTML-Review/{Providername}-{Tool}-{Model}-{Thinkinglevel/Effortlevel}-{Prompt version}/PROMPT.txt
2. one agent that just looks at the transcript we extracted. he delivers a REVIEW.md to Review/TRANSCRIPT-Review/{Providername}-{Tool}-{Model}-{Thinkinglevel/Effortlevel}-{Prompt version}. You save its chat transcript to TRANSCRIPT.md in Review/TRANSCRIPT-Review/{Providername}-{Tool}-{Model}-{Thinkinglevel/Effortlevel}-{Prompt version}. It's prompt gets saved to
  Review/TRANSCRIPT-Review/{Providername}-{Tool}-{Model}-{Thinkinglevel/Effortlevel}-{Prompt version}/PROMPT.txt
3. one agent that looks at the html file in Claude in Chrome. here it is important to have them run sequentially. you open an python server for the test, then you start the agent. he delivers a REVIEW.md to Review/Browser-Review/{Providername}-{Tool}-{Model}-{Thinkinglevel/Effortlevel}-{Prompt version}. You save its
  chat transcript to TRANSCRIPT.md in Review/Browser-Review/{Providername}-{Tool}-{Model}-{Thinkinglevel/Effortlevel}-{Prompt version}. It's prompt gets saved to
    Review/Browser-Review/{Providername}-{Tool}-{Model}-{Thinkinglevel/Effortlevel}-{Prompt version}/PROMPT.txt

This prompt and your chat transcript needs to be saved to
ReviewOrchestrator/{PROMPT,TRANSCRIPT}.md
