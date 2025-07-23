import re
import urllib.parse

from beanie import Document, Insert, Replace, Save, SaveChanges, after_event
from loguru import logger
from pydantic import ConfigDict

from env import settings


class Message(Document):
    msgid: str
    open_kfid: str | None = None
    external_userid: str | None = None
    send_time: int
    origin: int
    servicer_userid: str | None = None
    msgtype: str

    model_config = ConfigDict(extra="allow")

    @after_event(Insert, Save, Replace, SaveChanges)
    async def after_insert(self):
        if self.__pydantic_extra__ is None or self.external_userid is None:
            return
        logger.info(f"Message inserted: {self.model_dump_json()}")
        msg_content = "未知的消息"
        try:
            if self.msgtype == "miniprogram":
                miniprogram = self.__pydantic_extra__["miniprogram"]
                appid = miniprogram["appid"]
                if (
                    appid == "wx2c348cf579062e56" or appid == "wxde8ac0a21135c07d"
                ):  # 美团外卖/美团: https://linux.do/t/topic/743802
                    poiIdStr = ""

                    pagepath = miniprogram.get("pagepath", "")

                    if "?" in pagepath:
                        query_string = pagepath.split("?", 1)[1]
                        params = urllib.parse.parse_qs(query_string)
                        if "pageid" in params:
                            pageid = params["pageid"][0]
                            match = re.search(r"poi_id_str=([^&]+)", pageid)
                            if match:
                                poiIdStr = urllib.parse.unquote(match.group(1))
                        if not poiIdStr and "poi_id_str" in params:
                            poiIdStr = params["poi_id_str"][0]
                    settings.weixin_work.client.kf_message.send_msgmenu(
                        open_kfid=self.open_kfid,
                        user_id=self.external_userid,
                        head_content="美团万能津贴转换完成",
                        menu_list=[
                            {
                                "type": "miniprogram",
                                "miniprogram": {
                                    "appid": "wx2c348cf579062e56",
                                    "content": miniprogram.get("title", "美团"),
                                    "pagepath": f'packages/restaurant/restaurant/restaurant.html?poi_id_str={poiIdStr}&allowance_alliance_scenes=1100&poi_id=67890&ad_activity_flag={{"adActivityFlag":"100","type":0}}',
                                },
                            }
                        ],
                        tail_content="严禁外传，泄露该链接\nBy:Ocyss",
                    )
                    return
        except Exception as e:
            logger.error(f"Message inserted: {e}")
            msg_content = f"处理错误: {e}"
        settings.weixin_work.client.kf_message.send_text(
            open_kfid=self.open_kfid,
            user_id=self.external_userid,
            content=msg_content,
        )
