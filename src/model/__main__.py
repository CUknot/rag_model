# --- Step 1: Add a reasoning step ---
def reason_about_query(state: MessagesState) -> MessagesState:
    """Analyze user query and decide what tools or steps are needed."""
    user_message = state["messages"][-1]  # latest human message
    reasoning_prompt = (
        "You are a reasoning assistant, not a chatbot."
        "Your only task is to analyze the user query using step-by-step chain-of-thought (CoT) reasoning."
        "Your job is to think carefully about:\n"
        "- What the user is asking.\n"
        "- What information is required to answer it correctly.\n"
        "- Whether any tool needs to be used to retrieve that information.\n"
        "- What the next best step is to move forward.\n"
        "If a tool is needed, clearly state which tool should be called and what input should be given.\n"
        "\nIf the assistant can confidently respond using internal knowledge (e.g., prior context, known source, etc.), then state that no tool call is needed.\n"
        "\nStructure your response as a logical and concise reasoning trace, ending with a clear action recommendation such as:\n"
        "- 'retrieve_information': This tool is used to fetch relevant information based on a given query or context, enabling you to search knowledge bases, access data, and retrieve details from various sources with effort.\n"
        "- 'retrieve_room_info': This tool allows you to obtain specific details about individual rooms, such as size, amenities, capacity, location within a building, and booking status.\n"
        "  Args:\n"
        "    latitude: The latitude of the desired location.\n"
        "    longitude: The longitude of the desired location.\n"
        "    arrival_date: The check-in date (YYYY-MM-DD).\n"
        "    departure_date: The check-out date (YYYY-MM-DD).\n"
        "    adults: The number of adults.\n"
        "    children_age: A comma-separated string of children's ages.\n"
        "    room_qty: The number of rooms required.\n"
        "    price_min: The minimum price.\n"
        "    price_max: The maximum price.\n"
        "          This is used for geocoding if latitude and longitude are missing.\n"
        "- 'get_latitude_longitude': This tool is designed to return the precise latitude and longitude coordinates for a specified location, accepting addresses, cities, or landmarks as input.\n"
        "  Args:\n"
        "    location: The address, city, or landmark to get coordinates for.\n"
        "- \"No tool call is needed. Proceed to answer directly.\"\n"
        f"\nConsider the following user query:\n\"{user_message.content}\"\n"
        "You are helping the LLM plan its next move, not answering the user."
    )
    # Assuming 'llm_reasoning' is a defined Language Model instance
    reasoning_response = llm_reasoning.invoke(reasoning_prompt)
    return {"messages": state["messages"] + [SystemMessage(content=reasoning_response.content)]}

# Step 2: Generate an AIMessage that may include a tool-call to be sent.
def query_or_respond(state: MessagesState) -> MessagesState:
    """Generate tool call for retrieval or respond."""
    llm_with_tools = llm.bind_tools([retrieve_information, retrieve_room_info, get_latitude_longitude])
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}

# Step 3: Execute the retrieval.
tools = ToolNode([retrieve_information, retrieve_room_info, get_latitude_longitude])

# Step 4: Generate a response using the retrieved content.
def generate(state: MessagesState) -> MessagesState:
    """Generate answer."""
    recent_tool_messages = [msg for msg in reversed(state["messages"]) if msg.type == "tool"][::-1]
    docs_content = "\n\n".join(msg.content for msg in recent_tool_messages)
    system_message_content = (
        "You are a Booking.com chatbot, adept at assisting users with inquiries about hotels and rooms with precision."
        "Your primary goal is to provide helpful and informative answers in full, natural-sounding sentences."
        "Do not output code blocks or tool calls directly to the user."
        "Instead, use the information provided in the 'data from tools:' section below to construct your response."
        "For all questions pertaining to policies and terms, include a reference link specifying the source document and the corresponding page number if available in the tool data."
        "Ensure the accuracy of your responses by leveraging the retrieved information effectively."
        "When you answer about pricing, always include a reference to the website where you found the price if that information is available in the tool data. For example: 'The price is $100 (Source: booking.com)'. If a direct booking link is provided, you can also include that."
        "Maintain brevity in your responses, adhering to a maximum of three sentences for hotel and room-related inquiries."
        "data from tools:"
        f"{docs_content}"
    )
    conversation_messages = [
        message
        for message in state["messages"]
        if message.type in ("human", "system")
        or (message.type == "ai" and not message.tool_calls)
    ]
    prompt = [SystemMessage(content=system_message_content)] + conversation_messages
    response = llm.invoke(prompt)
    return {"messages": state["messages"] + [response]}
