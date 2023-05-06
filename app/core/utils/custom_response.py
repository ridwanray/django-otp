from rest_framework.response import Response


class CustomResponse():

    def Success(data, status=200, headers=None):
        dta1 = {'data': data, 'code': status, 'status': 'success'}
        return Response(dta1, status, headers=headers)

    def Failure(error, status=400, headers=None):
        dta1 = {'errors': error, 'code': status, 'status': 'failed'}
        return Response(dta1, status, headers=headers)
