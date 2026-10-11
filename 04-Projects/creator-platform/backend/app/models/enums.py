from enum import Enum


class SourcePlatform(str, Enum):
    """客户来源平台"""
    DOUYIN = "douyin"              # 抖音
    XIAOHONGSHU = "xiaohongshu"    # 小红书
    SHIPINHAO = "shipinhao"        # 视频号
    KUAISHOU = "kuaishou"          # 快手
    BILIBILI = "bilibili"          # B站
    WEIBO = "weibo"                # 微博
    ZHIHU = "zhihu"                # 知乎
    REFERRAL = "referral"          # 转介绍
    OFFLINE = "offline"            # 线下
    DIRECT = "direct"              # 直接添加
    OTHER = "other"


class Channel(str, Enum):
    """联系渠道"""
    PERSONAL_WECHAT = "personal_wechat"   # 个人微信
    WECHAT_WORK = "wechat_work"           # 企业微信
    FEISHU = "feishu"                      # 飞书
    PHONE = "phone"                        # 电话
    OTHER = "other"


class ContactStage(str, Enum):
    """客户旅程阶段"""
    FOLLOWER = "follower"                           # 粉丝（未入私域）
    PRIVATE_DOMAIN = "private_domain"               # 已入私域
    ENGAGED = "engaged"                             # 活跃互动
    INTENT_SHOWN = "intent_shown"                   # 表达咨询意向
    CONSULTATION_BOOKED = "consultation_booked"     # 已预约咨询
    CONVERTED = "converted"                         # 已成交
    ACTIVE_CLIENT = "active_client"                 # 活跃付费客户
    DORMANT = "dormant"                             # 沉默/不活跃
    CHURNED = "churned"                             # 流失


class ProductType(str, Enum):
    KNOWLEDGE_COURSE = "knowledge_course"       # 知识课程
    LIVE_COURSE = "live_course"                 # 直播课
    CONSULTATION_SINGLE = "consultation_single" # 单次咨询
    CONSULTATION_PACKAGE = "consultation_pkg"   # 咨询包
    HEALTH_PLAN = "health_plan"                 # 健管方案定制
    HEALTH_MGMT_SUB = "health_mgmt_sub"         # 健管订阅服务
    CUSTOM_PROGRAM = "custom_program"           # 定制化项目


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class HealthPlanStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ConsultationType(str, Enum):
    INITIAL = "initial"               # 初次咨询
    FOLLOWUP = "followup"             # 跟进回访
    HEALTH_REVIEW = "health_review"   # 健康复盘
    PLAN_DELIVERY = "plan_delivery"   # 方案交付
    PAID_SESSION = "paid_session"     # 付费咨询


class InteractionType(str, Enum):
    CONTENT_COMMENT = "content_comment"   # 内容评论
    CONTENT_DM = "content_dm"             # 内容私信
    WECHAT_ADD = "wechat_add"             # 加微信
    GROUP_JOIN = "group_join"             # 入群
    MESSAGE = "message"                    # 消息沟通
    VOICE_CALL = "voice_call"             # 语音通话
    VIDEO_CALL = "video_call"             # 视频通话
    PURCHASE = "purchase"                  # 购买
    HEALTH_CHECKIN = "health_checkin"     # 健康打卡
    REFERRAL_MADE = "referral_made"       # 发起转介绍


class AIActionType(str, Enum):
    FOLLOW_UP = "follow_up"                     # 建议跟进
    FLAG_HIGH_INTENT = "flag_high_intent"       # 标记高意向
    CHURN_WARNING = "churn_warning"             # 流失预警
    UPSELL_SUGGEST = "upsell_suggest"           # 升单建议
    REACTIVATE = "reactivate"                   # 唤醒沉默客户
    HEALTH_PLAN_REVIEW = "health_plan_review"   # 方案复盘提醒
    REFERRAL_REQUEST = "referral_request"       # 请求转介绍
    RENEWAL_REMINDER = "renewal_reminder"       # 续费提醒


class AIActionStatus(str, Enum):
    PENDING = "pending"       # 待审批
    APPROVED = "approved"     # 已通过
    REJECTED = "rejected"     # 已驳回
    EXPIRED = "expired"       # 已过期
    ACTED = "acted"           # 已执行


class ConsultantRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    CONSULTANT = "consultant"   # 健管顾问
    FDE = "fde"                 # 前线部署工程师
