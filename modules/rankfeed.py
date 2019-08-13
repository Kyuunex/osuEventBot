import feedparser
import aiohttp
import time
import asyncio

from modules import db
from modules.connections import osu as osu
from osuembed import osuembed


async def fetch_rss():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://osu.ppy.sh/feed/ranked/") as response:
                httpcontents = (await response.text())
                if len(httpcontents) > 4:
                    return httpcontents
                else:
                    return None
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in rankfeed.fetch")
        print(e)
        return None


def build_mapset_list(map_feed):
    mapset_list = []
    for one_mapset in map_feed['entries']:
        mapset_list.append(one_mapset['link'].split('http://osu.ppy.sh/s/')[1])
    return mapset_list


async def main(client):
    try:
        await asyncio.sleep(10)
        rankfeed_channel_list = db.query("SELECT channel_id FROM rankfeed_channel_list")
        if rankfeed_channel_list:
            print(time.strftime('%X %x %Z')+' | performing rankfeed check')
            fresh_entries = await fetch_rss()
            if fresh_entries:
                map_feed = feedparser.parse(fresh_entries)
                mapset_list = build_mapset_list(map_feed)
                for mapset_id in mapset_list:
                    if not db.query(["SELECT mapset_id FROM rankfeed_history WHERE mapset_id = ?", [str(mapset_id)]]):
                        embed = await osuembed.beatmapset(await osu.get_beatmapset(s=mapset_id))
                        if embed:
                            for rankfeed_channel_id in rankfeed_channel_list:
                                channel = client.get_channel(int(rankfeed_channel_id[0]))
                                if channel:
                                    await channel.send(embed=embed)
                                else:
                                    db.query(["DELETE FROM rankfeed_channel_list WHERE channel_id = ?", [str(rankfeed_channel_id[0])]])
                                    print("channel with id %s no longer exists so I am removing it from the list" % (str(rankfeed_channel_id[0])))
                            db.query(["INSERT INTO rankfeed_history VALUES (?)", [str(mapset_id)]])
            print(time.strftime('%X %x %Z')+' | finished rankfeed check')
        await asyncio.sleep(1600)
    except Exception as e:
        print(time.strftime('%X %x %Z'))
        print("in rankfeed_background_loop")
        print(e)
        await asyncio.sleep(3600)


async def add(channel):
    fresh_entries = await fetch_rss()
    if fresh_entries:
        map_feed = feedparser.parse(fresh_entries)
        mapset_list = build_mapset_list(map_feed)
        for mapset_id in mapset_list:
            if not db.query(["SELECT mapset_id FROM rankfeed_history WHERE mapset_id = ?", [str(mapset_id)]]):
                db.query(["INSERT INTO rankfeed_history VALUES (?)", [str(mapset_id)]])
        if not db.query(["SELECT * FROM rankfeed_channel_list WHERE channel_id = ?", [str(channel.id)]]):
            db.query(["INSERT INTO rankfeed_channel_list VALUES (?)", [str(channel.id)]])
            await channel.send(":ok_hand:")


async def remove(channel):
    db.query(["DELETE FROM rankfeed_channel_list WHERE channel_id = ?", [str(channel.id)]])
    await channel.send(":ok_hand:")