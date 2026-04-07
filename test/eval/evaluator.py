import json
import asyncio
import sys
import os
import time
from typing import Dict, List, Any

# 将 src 目录添加到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from agent.graph import graph_app
from utils.logger import logger

# 忽略节点内部日志，保持评测输出整洁
import logging
logging.getLogger("uvicorn").setLevel(logging.ERROR)

class GeoTraveEvaluator:
    """
    GeoTrave Agent 自动化评测器
    """
    
    def __init__(self, dataset_path: str):
        with open(dataset_path, "r", encoding="utf-8") as f:
            self.dataset = json.load(f)
        self.results = []

    def _calculate_match_score(self, expected: Dict, actual: Dict) -> float:
        """
        计算字段匹配得分 (Field Recall)
        支持嵌套字典和 Pydantic 模型的对比
        """
        total_fields = 0
        match_count = 0
        
        # 递归检查基础字段
        # 注意：Analyzer 节点会将 result.people_count 映射到 state['people']，
        # 而测试集预计字段为 people_count。这里需要统一映射逻辑。
        field_mapping = {
            "people_count": "people",
            "destination": "destination",
            "days": "days",
            "budget_limit": "budget_limit"
        }

        for exp_key, act_key in field_mapping.items():
            if exp_key in expected:
                total_fields += 1
                exp_val = expected.get(exp_key)
                act_val = actual.get(act_key)
                
                # 兼容处理：如果 act_val 是 Pydantic 需转 Dict
                if hasattr(act_val, "model_dump"):
                    act_val = act_val.model_dump()
                
                # 兼容 [start, end] 列表格式与单值格式
                if str(exp_val) == str(act_val):
                    match_count += 1
                elif isinstance(act_val, list) and exp_val in act_val:
                    match_count += 1
        
        # 核心：检查 hard_constraints 内部字段准确率
        exp_hc = expected.get("hard_constraints", {})
        act_hc_raw = actual.get("hard_constraints", {})
        
        # 将 Pydantic 对象转换为字典 (Analyzer 节点返回的是 HardConstraints 实例)
        act_hc = act_hc_raw.model_dump() if hasattr(act_hc_raw, "model_dump") else act_hc_raw

        if exp_hc:
            for hc_key, hc_val in exp_hc.items():
                total_fields += 1
                act_val = act_hc.get(hc_key)
                
                if isinstance(hc_val, list):
                    # 判断子集是否包含所有预期值
                    if isinstance(act_val, list) and all(item in act_val for item in hc_val):
                        match_count += 1
                elif str(hc_val) == str(act_val):
                    match_count += 1

        return round(match_count / total_fields, 2) if total_fields > 0 else 1.0

    async def run_eval(self):
        print(f"🚀 Starting Advanced Evaluation for {len(self.dataset)} cases...\n")
        print(f"{'ID':<25} | {'Score':<8} | {'Latency':<8} | {'Recall'}")
        print("-" * 75)
        
        for case in self.dataset:
            start_time = time.time()
            config = {"configurable": {"thread_id": f"eval_{case['id']}_{int(time.time())}"}}
            
            try:
                # 处理多轮对话或单轮输入
                state_output = {}
                if "multi_turn" in case:
                    for turn in case["multi_turn"]:
                        inputs = {"messages": [("user", turn)]}
                        state_output = await graph_app.ainvoke(inputs, config=config)
                else:
                    inputs = {"messages": [("user", case["input"])]}
                    state_output = await graph_app.ainvoke(inputs, config=config)
                
                latency = round(time.time() - start_time, 2)
                
                # 计算提取得分 (Field Recall)
                score = self._calculate_match_score(case["expected_state"], state_output)
                
                # 计算研究员召回质量 (Retrieval Check)
                retrieval_recall = "N/A"
                if "check_retrieval" in case["expected_state"]:
                    expected_keywords = case["expected_state"]["check_retrieval"]
                    context = state_output.get("retrieval_context", "") or ""
                    found_count = sum(1 for kw in expected_keywords if kw in context)
                    recall_rate = found_count / len(expected_keywords)
                    retrieval_recall = f"{recall_rate:.1%}"

                self.results.append({
                    "id": case["id"],
                    "score": score,
                    "latency": latency,
                    "retrieval_recall": retrieval_recall
                })
                
                # 打印结果
                status_color = "✅" if score >= 0.8 else "⚠️" if score >= 0.5 else "❌"
                print(f"{case['id']:<25} | {score:<8} | {latency:<8} | {retrieval_recall:<8} {status_color}")
                
            except Exception as e:
                print(f"❌ Error in Case {case['id']}: {str(e)}")
        
        self.summary()

    def summary(self):
        avg_score = sum(r["score"] for r in self.results) / len(self.results)
        avg_latency = sum(r["latency"] for r in self.results) / len(self.results)
        print("\n" + "="*50)
        print("📊 EVALUATION SUMMARY")
        print(f"Total Cases: {len(self.results)}")
        print(f"Average Field Recall: {avg_score:.2f}")
        print(f"Average Latency: {avg_latency:.2f}s")
        print("="*50)

if __name__ == "__main__":
    evaluator = GeoTraveEvaluator("test/eval/dataset.json")
    asyncio.run(evaluator.run_eval())
