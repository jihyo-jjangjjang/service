import pandas as pd
from konlpy.tag import *
import joblib

from .sentiment import predict_pn


def degree_cal(rate):
    if rate == 1 or rate == 5:
        return 3
    elif rate == 2 or rate == 4:
        return 2
    else:
        return 1


# N, V 비율 알려주는 함수
def NV_count(each_result):
    Nnum = 0
    Vnum = 0
    total = 0
    for element in each_result:
        total += 1
        if element[1] == 'Noun':
            Nnum += 1
        elif element[1][0] == 'V':
            Vnum += 1
    if total == 0:
        return '-1', '-1'
    return round(Nnum / total * 100, 2), round(Vnum / total * 100, 2)


def get_credibility_by_review(comment, rating):
    twitter = Twitter()

    total_p = pd.DataFrame({'사용자 ID': [0], '리뷰 내용': [comment], '별점': [rating]})

    total_p['리뷰 길이'] = total_p['리뷰 내용'].apply(lambda x: len(x))
    total_p['POS'] = total_p['리뷰 내용'].apply(lambda x: twitter.pos(x))

    total_p['degree'] = total_p['별점'].apply(lambda x: degree_cal(x))
    total_p['긍부정 예측_구분'] = predict_pn(comment)

    total_p['별점_긍부정 구분'] = total_p['별점'].apply(lambda x: 1 if x > 3 else 0)
    total_p['긍부정 예측_성공'] = total_p['긍부정 예측_구분'] - total_p['별점_긍부정 구분']
    total_p['긍부정 예측_성공'] = total_p['긍부정 예측_성공'].apply(lambda x: 1 if x == 0 else 0)


    total_p['N 비율'] = total_p['POS'].apply(lambda x: float(NV_count(x)[0]))
    total_p['V 비율'] = total_p['POS'].apply(lambda x: float(NV_count(x)[1]))
    non = total_p.loc[total_p['N 비율'] == -1].index
    total_p = total_p.drop(non)

    # groupby
    reviewer = total_p.groupby('사용자 ID').aggregate(
        {'별점': ['mean', 'std'], '사용자 ID': 'count', '리뷰 길이': ['mean', 'std'], 'degree': 'mean', '별점_긍부정 구분': 'sum',
         '긍부정 예측_성공': 'sum', 'N 비율': ['mean', 'std'], 'V 비율': ['mean', 'std']})
    reviewer = reviewer.fillna(0)

    reviewer.columns = ['별점_평균', '별점_표준편차', '리뷰 개수', '리뷰 길이_평균', '리뷰 길이_표준편차',
                        'degree_평균', '긍정 리뷰 개수', '긍부정 예측 일치 비율',
                        'N 비율_평균', 'N 비율_표준편차', 'V 비율_평균', 'V 비율_표준편차']
    reviewer['긍부정 예측 일치 비율'] = reviewer['긍부정 예측 일치 비율'] / reviewer['리뷰 개수'] * 100

    reviewer.columns = ['별점_평균', '별점_표준편차', '리뷰 개수', '리뷰 길이_평균', '리뷰 길이_표준편차',
                        'degree_평균', '긍정 리뷰 개수', '긍부정 예측 일치 비율',
                        'N 비율_평균', 'N 비율_표준편차', 'V 비율_평균', 'V 비율_표준편차']
    reviewer['긍부정 예측 일치 비율'] = reviewer['긍부정 예측 일치 비율'] / reviewer['리뷰 개수'] * 100
    reviewer = reviewer.reset_index()
    reviewer = reviewer.drop(['사용자 ID'], axis=1)

    loaded_model = joblib.load('app/files/k_means.pkl')
    pred_new = loaded_model.predict(reviewer)
    reviewer['군집'] = pred_new

    for i in reviewer['군집']:
        if i == 3:
            x = 5
        if i == 5:
            x = 3
        if i == 4:
            x = 1
        if i == 0:
            x = -1
        if i == 2:
            x = -3
        if i == 1:
            x = -5
    for j in reviewer['별점_평균']:
        if j == 1 or j == 5:
            y = -5
        if j == 2 or j == 4:
            y = 5
        if j == 3:
            y = 0
    reviewer['군집신뢰점수'] = x
    reviewer['degree점수'] = y

    return 80 + reviewer.iloc[0, :]['degree점수'] + reviewer.iloc[0, :]['군집신뢰점수'] - reviewer.iloc[0, :]['N 비율_평균'] * 5 / 100 + reviewer.iloc[0, :]['V 비율_평균'] * 5 / 100

    # reviewer['조정 별점'] = reviewer['별점_평균'] * reviewer['신뢰도'] / 100

