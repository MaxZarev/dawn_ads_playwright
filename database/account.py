from tortoise import Model, fields

class Account(Model):
    profile = fields.IntField(pk=True)
    email = fields.CharField(max_length=255, unique=True)
    registration_status = fields.BooleanField(default=False)
    confirm_status = fields.BooleanField(default=False)
    login_status = fields.BooleanField(default=False)
    tasks_status = fields.BooleanField(default=False)
    points = fields.CharField(max_length=255, default='0')

    class Meta:
        table = "accounts"

    @classmethod
    async def get_account(cls, profile: int):
        return await cls.get_or_none(profile=profile)

    @classmethod
    async def get_accounts(cls):
        return await cls.all()

    @classmethod
    async def create_account(cls, profile: int, email: str):
        account = await cls.get_account(profile=profile)
        if account is None:
            account = await cls.create(profile=profile, email=email)
            return account
        else:
            account.email = email
            await account.save()
            return account
    @classmethod
    async def change_status(cls, profile: int, status_name: str):
        account = await cls.get_account(profile=profile)
        if account is None:
            return
        if status_name == "registration":
            account.registration_status = True
        elif status_name == "confirm":
            account.confirm_status = True
        elif status_name == "login":
            account.login_status = True
        elif status_name == "tasks":
            account.tasks_status = True
        await account.save()

    @classmethod
    async def set_points(cls, profile: int, points: str):
        account = await cls.get_account(profile=profile)
        account.points = points
        await account.save()
