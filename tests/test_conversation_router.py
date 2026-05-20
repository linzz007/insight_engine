from insight_engine.conversation.router import detect_intent


def test_detect_intent_for_daily_news_report():
    assert detect_intent("帮我生成今日新闻分析报告") == "daily_news_report"


def test_detect_intent_for_normal_chat():
    assert detect_intent("你好，介绍一下这个项目") == "chat"

