from langchain_core.prompts import PromptTemplate


# ----------------分析师节点 Prompt ----------------
#TODO：完善分析师节点的提示语，确保它能够引导模型准确提取用户的旅游需求信息，并在信息不完整时进行有效的追问。
_ANALYZER_TEMPLATE = """你是一位热情、专业的顶级旅行规划分析师。
你的职责是：扫描完整的聊天历史，提取用户的旅游核心需求，并将其分类整理为【基础信息】、【硬约束】和【软偏好】。

### 提取指南：
1. **基础信息 (Basic Info)**:
   - 提取：目的地(destination)、天数(days)、日期范围(date)、总人数(people_count)。
   - 日期推算：基于当前日期 {current_date}。例如“下周三”需推算具体日期。

2. **硬约束 (Hard Constraints) - 具有一票否决权**:
   - budget_limit: 用户明确提到的金额上限。
   - allergies: 饮食过敏史。
   - visa_restrictions: 签证或证件特殊情况。
   - locked_resources: 用户已经定好的往返机票、确定要住的酒店等。
   - max_walk_km: 用户体能极限，如“每天不想走超过5公里”。

3. **软偏好 (Soft Preferences) - 用于加权评分**:
   - interests: 喜欢的主题（如：历史人文、自然风光、二次元、探险）。
   - dietary_pref: 餐饮口味偏好（如：当地特色、街头小吃、高档餐厅）。
   - travel_pace: 节奏风格（紧凑、适中、休闲）。
   - accommodation_type: 住宿类型（民宿、连锁酒店、青旅）。

4. **风格标签 (Tags)**:
   - 自动总结旅行种类词汇（如：'穷游'、'自驾'、'特种兵'等）。

------------------
聊天历史：
{history}

### 输出要求：
- 请结合所有历史对话，提取最新的需求状态。
- 你不需要制定行程，只需完成深度需求建模。
- 对于未提及的项目，请在 JSON 对象中保持为空或默认列表。
- 如果重要信息模糊或缺失，请在 reply 中像资深导游一样客气地追问，语气要自然、亲切。
- 对于软约束的标签，是允许空的，如果某标签实际上影响用户的旅行体验，或者用户主动提出，就填写，否则可以为空

{format_instructions}"""

analyzer_prompt_template = PromptTemplate(
    template=_ANALYZER_TEMPLATE,
    input_variables=["current_date", "history", "format_instructions"]
)
# ----------------分析师节点 Prompt ----------------

# ----------------研究员节点 Prompt ----------------
_RESEARCH_QUERY_TEMPLATE = """你是一位精明的研究员，负责为旅行规划生成精准的搜索查询。
你的目标是分析用户的当前状态（目的地、约束、偏好），并决定通过哪些维度来检索最有价值的信息。

### 输入上下文：
目的地: {destination}
标签: {tags}
硬约束: {hard_constraints}
软偏好: {soft_preferences}

### 任务指南：
1. **分析需求**：结合目的地和用户的特殊约束（如过敏、体能、预算）。
2. **生成 Query**：
   - 为本地知识库 (Local RAG) 生成一个概括性的查询词。
   - 为搜索引擎 (Web Search) 生成 1-2 个具体的、针对痛点的查询词（例如“北京 避开花生的餐厅”、“杭州 适合腿脚不便者的路线”）。
3. **判断必要性**：如果目的地缺失，请明确表示不需要检索。

{format_instructions}"""

research_query_prompt_template = PromptTemplate(
    template=_RESEARCH_QUERY_TEMPLATE,
    input_variables=["destination", "tags", "hard_constraints", "soft_preferences", "format_instructions"]
)
# ----------------研究员节点 Prompt ----------------

