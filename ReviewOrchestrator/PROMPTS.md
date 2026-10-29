# User prompts of the orchestrator session

Every message the user typed in this session, verbatim and in order. Teammate messages, tool results and question-dialog answers are excluded; the answers are in TRANSCRIPT.md.
Prompt 1 is an earlier, line-wrapped and truncated copy of Prompt 2 that the session log also recorded; it is kept as logged.

## Prompt 1 · 2026-10-29T20:30:12.616Z

````
here is a list of ai chats with different web tools:
first prompt:
https://chatgpt.com/c/6ae355ca-17a4-83eb-b26b-38244eb1971e
https://claude.ai/chat/09e85d21-ad05-4fe0-b10d-8ef14cc23da7

refined prompt after i saw the thinking output of the first prompt even before there results are
in:
https://claude.ai/chat/0a5ff96f-8165-4dec-b69e-0a0723d7d286
  https://chatgpt.com/c/6ae356bd-fa4c-83eb-8b2c-5a777b52333a
  https://chat.mistral.ai/code/01a18896-7c9a-7259-a8b0-1021401b8abd/01a18897-02b1-723e-8eac-66f06540e
  b7a
  https://gemini.google.com/app/bb0b8f672792cf16
  https://github.com/copilot/tasks/b471892c-1453-4af2-92fa-5f94611b2a73
  https://github.com/copilot/tasks/1976d0f6-45af-48c0-b323-2ce130b5afeb


  Extract the html file from all chats into a folder named
````

## Prompt 2 · 2026-10-29T20:44:35.332Z

````
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
````

## Prompt 3 · 2026-10-29T21:42:54.636Z

````
the current reviewer has problem: he cannot click that popup [Image #4] i am click it for him but he reclicks
````

## Prompt 4 · 2026-10-29T22:19:21.919Z

````
end all those agents you started and that are finished. they are still idling and hanging around.

make sure everything we did until now is tracable and written down.

when you are ready we are going to enter a new plan phase.
````

## Prompt 5 · 2026-10-29T22:40:52.588Z

````
[Entering plan mode.]

We need 5 more agents as Opus 5.5 high so it stays fair:
1. html judge: Output folder: Judge/HTML-Judge: get's all html files anonymised and creates a ranking - best to worst - also highlights elements that are special like features others lack, libaries noone else uses
2. transcript judge: Output folder: Judge/TRANSCRIPT-Judge: get's all transcripts anonymised and creates a ranking - best to worst - also highlights elements that are unique like good explaination what it created, reasoning for decisions, hallucinations
3. html + transcript judge: Output folder: Judge/HTML_TRANSCRIPT-Judge: get's all html files + transcripts anonymised and creates a ranking - best to worst - highlighting special features, differences to the norm
4. browser judge: Output folder: Judge/Browser-Judge: does anonymised Claude in Chrome runs for all implementations and creates a ranking - best to worst - highlighting what differentiates a product from the others
5. browser+html judge: Outfolder: Judge/Browser_HTML-Judge: get's all html files anonymised and tests the products in Claude in Chrome and creates a ranking - best to worst - highlighting how the code influenced the result

all judges need to add a short justification <50 Words for each element of their ranking and their ranking criterias and why they selected the special elements in one sentence. they should also add a short <200 Words summary of their tests and approaches.

for claude in chrome runs their prompts should contain to look for browser alter lines and switch them to console.log().

we want to save the prompt, transcript and result to the output folders
````

## Prompt 6 · 2026-10-29T23:19:34.683Z

````
status? we are waiting for 12 minutes for the judge 5's shutdown confirmation
````

## Prompt 7 · 2026-10-29T23:23:09.847Z

````
wrap your session here. save your transcript + prompts
````
