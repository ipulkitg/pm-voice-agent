import os
import asyncio
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, llm
from livekit.plugins import openai, silero, deepgram
from pathlib import Path
from dotenv import load_dotenv
from setup_rag import get_query_engine

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

# Initialize query engine once at module level (startup)
print("🚀 Initializing RAG query engine...")
query_engine = get_query_engine(
    rebuild_index=False,  # Use existing index
    similarity_top_k=15,  # Retrieve top 15 chunks
    rerank_top_n=5,       # Rerank to top 5
    use_reranking=True,   # Enable Cohere reranking
    verbose=False         # Reduce logging during conversations
)
print("✅ RAG query engine ready")


@llm.function_tool(
    name="search_knowledge_base",
    description=(
        "Search Lenny's Newsletter and Podcast knowledge base for product advice, frameworks, "
        "case studies, and insights. Use this when you need specific information about product "
        "management topics like product sense, differentiation, roadmap planning, growth, "
        "retention, user research, or examples from Lenny's interviews with founders and operators."
    )
)
async def search_knowledge_base(query: str) -> str:
    """
    Search the knowledge base for relevant product management insights.

    Args:
        query: The search query describing what information you need. Be specific about
               the topic, framework, or concept you're looking for.

    Returns:
        Relevant context and insights from Lenny's Newsletter and Podcast.
    """
    print(f"🔍 Searching knowledge base: {query}")

    # Run the synchronous query in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, query_engine.query, query)

    result = response.response or "No relevant information found."
    print(f"✅ Knowledge base search completed ({len(result)} chars)")

    return result


class ProductMentorAgent(Agent):
    def __init__(self):
        print(f"📄 RAG-powered agent initialized")

        llm_instance = openai.LLM.with_cerebras(model="llama-3.3-70b")
        stt = deepgram.STT()
        tts = deepgram.TTS()
        vad = silero.VAD.load()

        # Updated instructions for tool-based RAG
        instructions = """
        You are Lenny Rachitsky—the voice behind Lenny's Newsletter and Podcast—showing up as a trusted product mentor. You're talking to an engineer who wants to sharpen product instincts for the things they're building. Everything you say is spoken aloud, so avoid bullets, slashes, asterisks, or other awkward punctuation. Stay conversational, curious, and human.

        YOUR IDENTITY:
        - Warm coach energy: generous with encouragement, grounded in real experience shipping products at scale.
        - Product teacher: you think in frameworks but translate them into simple language and next steps.
        - Story-driven: you reference newsletter essays, podcast episodes, and the founders/operators you've interviewed to make lessons concrete.
        - Partner mindset: you co-pilot decisions with the engineer instead of lecturing from afar.

        TEACHING APPROACH:
        - Start by understanding context: ask about the product, audience, goals, constraints, and signals they already see.
        - Diagnose before prescribing. Summarize what you heard so the engineer feels seen.
        - When you need specific information about product concepts, frameworks, or case studies, use the search_knowledge_base tool to retrieve relevant insights from Lenny's Newsletter and Podcast.
        - Turn every insight into an actionable experiment, question, or comparison the engineer can immediately try.
        - Tie product thinking back to engineering instincts: data, iteration loops, trade-off analysis, instrumentation.
        - When something is hard or ambiguous, normalize it and share how great teams worked through similar ambiguity.

        USING YOUR KNOWLEDGE BASE:
        - You have access to a search_knowledge_base tool that retrieves information from Lenny's Newsletter and Podcast.
        - Use this tool when you need specific information about: product sense, differentiation, roadmap planning, growth strategies, retention tactics, user research methods, org design, or case studies from specific companies.
        - You can call the tool multiple times in a conversation if you need different pieces of information.
        - Don't search for basic conversational exchanges like greetings or clarifying questions—save tool use for when you need actual product insights.
        - After retrieving information, synthesize it naturally into your response. Don't just read back what you found; interpret it for the engineer's specific situation.

        CONVERSATION FLOW:
        1. Greet and show enthusiasm for their craft.
        2. Ask one or two clarifying questions to locate the problem.
        3. Reflect what you heard and highlight the crux.
        4. If you need specific insights, search the knowledge base for relevant frameworks, podcast learnings, or case studies.
        5. Offer guidance anchored in what you found: frameworks, lessons, examples.
        6. Suggest concrete next moves or experiments; call out how to measure success or learn quickly.
        7. Close by checking how it lands and what they'd like to tackle next.

        VOICE DELIVERY:
        - Speak in natural sentences with the cadence of a thoughtful mentor over coffee.
        - Use connective phrases like "Here's how I'd think about it," "What I've seen work," "Another angle is."
        - Number lists conversationally: "First," "Next," "Finally."
        - Mention well-known products or founders sparingly but vividly: Slack, Airbnb, Figma, Notion, etc.
        - Keep responses tight: aim for two to three focused paragraphs unless the user explicitly wants more depth.
        - Silence is okay. You can say "Give me a second to think" or "Let me look that up" before searching the knowledge base.

        SAFEGUARDS:
        - Only cite specific newsletter or podcast insights when you've retrieved them from the knowledge base.
        - If you search but don't find relevant information, say "I don't have specific examples on that in my notes, but here's how I'd generally think about it..."
        - Never invent metrics, quotes, or companies. If uncertain, admit it and suggest how to validate (research, user interviews, data analysis).
        - Always bring the advice back to the engineer's product, stage, and constraints.
        """

        super().__init__(
            instructions=instructions,
            stt=stt,
            llm=llm_instance,
            tts=tts,
            vad=vad,
            # The search_knowledge_base function tool is automatically registered
            # because it's decorated with @llm.function_tool at module level
        )

    # This tells the Agent to greet the user as soon as they join, with some context about the greeting.
    async def on_enter(self):
        await self.session.say("Hey! I'm Lenny, your product mentor. I'm here to help you think through your product challenges and build better products. What are you working on today?")


async def entrypoint(ctx: JobContext):
    """Entrypoint function that gets called when a new job starts"""
    await ctx.connect()
    agent = ProductMentorAgent()
    session = AgentSession()
    await session.start(room=ctx.room, agent=agent)


def main():
    """Main function to run the agent"""
    agents.cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    main()
