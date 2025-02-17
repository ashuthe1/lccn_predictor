import asyncio
from typing import List, Optional

from fastapi import APIRouter, Request
from loguru import logger
from pydantic import BaseModel, NonNegativeInt, conint, conlist

from api.utils import check_contest_name
from app.db.models import ContestRecordArchive, ContestRecordPredict, KeyOfUser

router = APIRouter(
    prefix="/contest-records",
    tags=["contest_records"],
)


@router.get("/count")
async def contest_records_count(
    request: Request,
    contest_name: str,
    archived: Optional[bool] = False,
) -> int:
    """
    Count records of a given contest.
    By default, count predicted contests only.
    Count archived contests when setting `archived = True` explicitly.
    :param request:
    :param contest_name:
    :param archived:
    :return:
    """
    logger.info(f"{request.client=}")
    await check_contest_name(contest_name)
    if not archived:
        total_num = await ContestRecordPredict.find(
            ContestRecordPredict.contest_name == contest_name,
            ContestRecordPredict.score != 0,
        ).count()
    else:
        total_num = await ContestRecordArchive.find(
            ContestRecordArchive.contest_name == contest_name,
            ContestRecordArchive.score != 0,
        ).count()
    return total_num


@router.get("/")
async def contest_records(
    request: Request,
    contest_name: str,
    archived: Optional[bool] = False,
    skip: Optional[NonNegativeInt] = 0,
    limit: Optional[conint(ge=1, le=100)] = 25,
) -> List[ContestRecordPredict | ContestRecordArchive]:
    """
    Query all records of a given contest.
    By default, query predicted contests only.
    Query archived contests when setting `archived = True` explicitly.
    :param request:
    :param contest_name:
    :param archived:
    :param skip:
    :param limit:
    :return:
    """
    logger.info(f"{request.client=}")
    await check_contest_name(contest_name)
    if not archived:
        records = (
            await ContestRecordPredict.find(
                ContestRecordPredict.contest_name == contest_name,
                ContestRecordPredict.score != 0,
            )
            .sort(ContestRecordPredict.rank)
            .skip(skip)
            .limit(limit)
            .to_list()
        )
    else:
        records = (
            await ContestRecordArchive.find(
                ContestRecordArchive.contest_name == contest_name,
                ContestRecordArchive.score != 0,
            )
            .sort(ContestRecordArchive.rank)
            .skip(skip)
            .limit(limit)
            .to_list()
        )
    return records


@router.get("/user")
async def contest_records_user(
    request: Request,
    contest_name: str,
    username: str,
    archived: Optional[bool] = False,
) -> List[ContestRecordPredict | ContestRecordArchive]:
    """
    Query records of a given contest by username.
    By default, query predicted contests only.
    Query archived contests when setting `archived = True` explicitly.
    :param request:
    :param contest_name:
    :param username:
    :param archived:
    :return:
    """
    logger.info(f"{request.client=}")
    await check_contest_name(contest_name)
    if not archived:
        records = await ContestRecordPredict.find(
            ContestRecordPredict.contest_name == contest_name,
            ContestRecordPredict.username == username,
            ContestRecordPredict.score != 0,
        ).to_list()
    else:
        records = await ContestRecordArchive.find(
            ContestRecordArchive.contest_name == contest_name,
            ContestRecordArchive.username == username,
            ContestRecordArchive.score != 0,
        ).to_list()
    return records


class RequestOfContestRecords(BaseModel):
    contest_name: str
    users: conlist(KeyOfUser, min_items=1, max_items=26)


class ResultOfContestRecordPredict(BaseModel):
    old_rating: Optional[float] = None
    new_rating: Optional[float] = None
    delta_rating: Optional[float] = None


@router.post("/predicted-rating")  # formal route
async def predicted_rating(
    request: Request,
    query: RequestOfContestRecords,
) -> List[Optional[ResultOfContestRecordPredict]]:
    """
    Query multiple predicted records in a contest.
    :param request:
    :param query:
    :return:
    """
    logger.info(f"{request.client=} {request.url.path=}")
    await check_contest_name(query.contest_name)
    tasks = (
        ContestRecordPredict.find_one(
            ContestRecordPredict.contest_name == query.contest_name,
            ContestRecordPredict.data_region == user.data_region,
            ContestRecordPredict.username == user.username,
            projection_model=ResultOfContestRecordPredict,
        )
        for user in query.users
    )
    return await asyncio.gather(*tasks)


class RequestOfRealTimeRank(BaseModel):
    contest_name: str
    user: KeyOfUser


class ResultOfRealTimeRank(BaseModel):
    real_time_rank: Optional[list]


@router.post("/real-time-rank")
async def real_time_rank(
    request: Request,
    query: RequestOfRealTimeRank,
) -> ResultOfRealTimeRank:
    """
    Query user's realtime rank list of a given contest.
    :param request:
    :param query:
    :return:
    """
    logger.info(f"{request.client=}")
    await check_contest_name(query.contest_name)
    return await ContestRecordArchive.find_one(
        ContestRecordArchive.contest_name == query.contest_name,
        ContestRecordArchive.data_region == query.user.data_region,
        ContestRecordArchive.username == query.user.username,
        projection_model=ResultOfRealTimeRank,
    )
