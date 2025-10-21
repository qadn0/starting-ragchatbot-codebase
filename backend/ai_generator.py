import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Tool Usage:
- **Content search tool**: Use for questions about specific course content or detailed educational materials
- **Course outline tool**: Use for questions about course structure, lessons list, or course overview
- **Multiple tool calls allowed**: You may call tools sequentially (up to 2 rounds) if needed to fully answer the question
- **Strategic tool use**: Search content first, then get outline if structure questions remain, or search multiple times with refined queries
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course content questions**: Use the content search tool first, then answer
- **Course outline/structure questions**: Use the course outline tool to retrieve the course title, course link, lesson count, and complete list of lesson numbers and titles
- **Follow-up searches**: If initial results are insufficient, you may search again with refined parameters
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "based on the tool results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str, max_tool_rounds: int = 2):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tool_rounds = max_tool_rounds

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with support for up to max_tool_rounds of sequential tool calling.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize message chain
        messages = [{"role": "user", "content": query}]

        # If no tools provided, make direct API call
        if not tools or not tool_manager:
            response = self.client.messages.create(
                **self.base_params,
                messages=messages,
                system=system_content
            )
            return self._extract_text_response(response)

        # Iterative loop for tool calling rounds
        for round_num in range(self.max_tool_rounds):
            # Make API call with tools available
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content,
                "tools": tools,
                "tool_choice": {"type": "auto"}
            }

            response = self.client.messages.create(**api_params)

            # Termination condition: Claude chose not to use tools
            if response.stop_reason != "tool_use":
                return self._extract_text_response(response)

            # Claude requested tool use - execute and append results
            messages.append({"role": "assistant", "content": response.content})

            # Execute tools and add results to messages
            tool_results = self._execute_tools(response.content, tool_manager)
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        # Max rounds reached - make final call without tools to force answer
        return self._make_final_call(messages, system_content)

    def _execute_tools(self, content_blocks, tool_manager) -> List[Dict[str, Any]]:
        """
        Execute all tool calls from response content.

        Args:
            content_blocks: Response content containing tool_use blocks
            tool_manager: Manager to execute tools

        Returns:
            List of tool result dictionaries
        """
        tool_results = []
        for content_block in content_blocks:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name,
                        **content_block.input
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })
                except Exception as e:
                    # Add error as tool result for graceful degradation
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": f"Error executing tool: {str(e)}",
                        "is_error": True
                    })

        return tool_results

    def _extract_text_response(self, response) -> str:
        """
        Extract text content from API response.

        Args:
            response: API response object

        Returns:
            Text string from response
        """
        for content_block in response.content:
            if hasattr(content_block, 'type') and content_block.type == "text":
                return content_block.text
            elif hasattr(content_block, 'text'):
                # Handle mock objects or direct text attributes
                return content_block.text

        # Fallback if no text found
        return "I apologize, but I couldn't generate a response."

    def _make_final_call(self, messages: List[Dict[str, Any]], system_content: str) -> str:
        """
        Make final API call without tools to force Claude to provide an answer.

        Args:
            messages: Accumulated message history
            system_content: System prompt content

        Returns:
            Final response text
        """
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
            # Explicitly no tools parameter
        }

        final_response = self.client.messages.create(**final_params)
        return self._extract_text_response(final_response)