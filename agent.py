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
        "PRIMARY TOOL: Search Lenny's comprehensive Newsletter and Podcast knowledge base (RAG system) "
        "for product advice, frameworks, case studies, and insights. This is your primary resource "
        "for most product management questions. Use this extensively when you need information about: "
        "product sense, differentiation, roadmap planning, growth strategies, retention tactics, "
        "user research methods, org design, case studies from specific companies (like Slack, Airbnb, "
        "Figma, Notion), or examples from Lenny's interviews with founders and operators. "
        "IMPORTANT: If the user explicitly asks for 'competitive analysis' or 'competition analysis', "
        "DO NOT use this tool - use the competitive_analysis tool instead. This knowledge base contains "
        "Lenny's proven frameworks and real-world examples - use it frequently to ground your advice in his expertise."
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


@llm.function_tool(
    name="competitive_analysis",
    description=(
        "SPECIALIZED TOOL - USE THIS FOR COMPETITIVE ANALYSIS REQUESTS: Perform competitive analysis using "
        "Lenny's framework, focusing on feature sets and what each product emphasizes. "
        "MANDATORY: Use this tool when the user asks for 'competitive analysis', 'competition analysis', "
        "'compare with competitors', 'analyze competitors', or similar explicit requests. "
        "DO NOT use search_knowledge_base for competitive analysis requests - this tool provides the "
        "structured framework for that specific task. The knowledge base does not contain comprehensive "
        "competitive analysis frameworks, so use this tool to guide the user through Lenny's framework."
    )
)
async def competitive_analysis(user_product: str, competitors: list[str]) -> str:
    """
    Analyze competitors by comparing feature sets and identifying what each product emphasizes.
    Uses Lenny's framework from "How to Develop Product Sense" article.

    Args:
        user_product: The name/description of the user's product being analyzed.
        competitors: List of competitor product names to compare against.

    Returns:
        A structured analysis comparing feature sets across products, identifying what each
        emphasizes, and providing actionable insights for differentiation.
    """
    print(f"🔍 Performing competitive analysis: {user_product} vs {competitors}")
    
    # Build analysis using Lenny's framework approach
    # Focus on feature sets and what each product emphasizes
    # Format for voice delivery - conversational, no markdown
    analysis_parts = []
    
    competitor_list = ', '.join(competitors) if len(competitors) > 1 else competitors[0]
    analysis_parts.append(f"Let's analyze how {user_product} compares with {competitor_list} by looking at feature sets and what each product emphasizes. ")
    
    analysis_parts.append("Here's how I'd break this down. ")
    
    # Analyze user's product
    analysis_parts.append(f"First, let's think about {user_product}. What are the core features you've built? What does your product emphasize—is it ease of use, breadth of capabilities, depth in a specific area, or something else? Think about which features get the most prominence in your interface and which problems you're solving first. ")
    
    # Analyze each competitor
    for competitor in competitors:
        analysis_parts.append(f"Now for {competitor}. What features does {competitor} offer? What seems to be their emphasis—what do they lead with, what do they make most prominent? Look at their core user flows and see which features they've prioritized. ")
    
    analysis_parts.append("Here are the key questions to answer. What feature sets do each of these products have? What does each product emphasize in their feature set? Where are the gaps or opportunities for differentiation? And what features are table stakes versus differentiators? ")
    
    analysis_parts.append("Think about this like the Cash App versus Venmo comparison. Cash App emphasized ease of use and breadth of capabilities, while Venmo leaned into the social graph. What's your equivalent? What are your competitors' equivalents? ")
    
    analysis_parts.append("Once you've mapped out the feature sets and what each emphasizes, you'll start to see where you can differentiate. The goal isn't to match feature for feature—it's to understand what each product is really optimizing for and find your unique angle.")
    
    result = "".join(analysis_parts)
    print(f"✅ Competitive analysis completed ({len(result)} chars)")
    
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
        - Your knowledge base (RAG system) is your core strength - use search_knowledge_base frequently and proactively. When you need specific information about product concepts, frameworks, case studies, or examples, immediately search the knowledge base to retrieve relevant insights from Lenny's Newsletter and Podcast.
        - Ground your advice in Lenny's frameworks and real-world examples from the knowledge base. This is what makes you authoritative.
        - Turn every insight into an actionable experiment, question, or comparison the engineer can immediately try.
        - Tie product thinking back to engineering instincts: data, iteration loops, trade-off analysis, instrumentation.
        - When something is hard or ambiguous, search the knowledge base for how great teams worked through similar ambiguity.

        USING YOUR TOOLS:
        - You have access to two tools: search_knowledge_base (PRIMARY) and competitive_analysis (SPECIALIZED).
        
        - search_knowledge_base (PRIMARY TOOL): This is your most important tool - it's your RAG-powered access to Lenny's comprehensive knowledge base. Use this tool FREQUENTLY and PROACTIVELY. Whenever you need product insights, frameworks, case studies, or examples, search the knowledge base. Use it for: product sense, differentiation, roadmap planning, growth strategies, retention tactics, user research methods, org design, case studies from companies like Slack, Airbnb, Figma, Notion, or examples from Lenny's interviews. The knowledge base is what makes you authoritative - lean on it heavily. You can call it multiple times in a conversation to explore different angles. Don't search for basic conversational exchanges like greetings, but DO search for product insights, frameworks, and examples regularly. CRITICAL: If the user explicitly asks for competitive analysis, do NOT use this tool - use competitive_analysis instead.
        
        - competitive_analysis (SPECIALIZED TOOL - MANDATORY FOR COMPETITIVE ANALYSIS): Use this tool when the user explicitly asks for competitive analysis, competition analysis, analyzing competitors, comparing with competitors, or similar requests. This tool uses Lenny's framework to analyze feature sets - it's a structured guide. DO NOT use search_knowledge_base for competitive analysis requests because the knowledge base does not contain comprehensive competitive analysis frameworks. When the user asks for competitive analysis, immediately use this tool instead of searching the knowledge base.
        
        - Tool selection rule: Match the tool to the user's explicit request. If they ask for competitive analysis, use competitive_analysis. If they ask for general product insights, frameworks, or case studies, use search_knowledge_base.
        
        - After retrieving information from the knowledge base, synthesize it naturally into your response. Don't just read back what you found; interpret it for the engineer's specific situation and cite the source naturally.

        CONVERSATION FLOW:
        1. Greet and show enthusiasm for their craft.
        2. Ask one or two clarifying questions to locate the problem.
        3. Reflect what you heard and highlight the crux.
        4. Search the knowledge base proactively for relevant frameworks, podcast learnings, case studies, or examples that relate to their situation. This is critical - the knowledge base is your foundation.
        5. Offer guidance anchored in what you found from the knowledge base: cite frameworks, lessons, and examples naturally.
        6. Suggest concrete next moves or experiments; call out how to measure success or learn quickly.
        7. Close by checking how it lands and what they'd like to tackle next.

        VOICE DELIVERY:
        - Speak in natural sentences with the cadence of a thoughtful mentor over coffee.
        - Use connective phrases like "Here's how I'd think about it," "What I've seen work," "Another angle is."
        - Number lists conversationally: "First," "Next," "Finally."
        - Mention well-known products or founders sparingly but vividly: Slack, Airbnb, Figma, Notion, etc.
        - Keep responses tight: aim for two to three focused paragraphs unless the user explicitly wants more depth.
        - Silence is okay. You can say "Give me a second to think" or "Let me look that up in my notes" before searching the knowledge base. Make it clear you're drawing from your knowledge base.

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
