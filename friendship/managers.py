from django.db.models import QuerySet, Q


class FriendRequestQuerySet(QuerySet):

    def filter_by_user(self, user):
        return self.filter(
            Q(to_user=user) | Q(from_user=user)
        )

    def get(self, *args, **kwargs):
        from friendship.models import FriendRequest

        user_a, user_b = kwargs.get("user_a", None), kwargs.get("user_b", None)
        if user_a and user_b:
            try: return self.get(to_user=user_a, from_user=user_b)
            except FriendRequest.DoesNotExist: pass
            try: return self.get(to_user=user_b, from_user=user_a)
            except FriendRequest.DoesNotExist: return None
        return super().get(*args, **kwargs)


class FriendshipQuerySet(QuerySet):

    def filter_by_user(self, user):
        return self.filter(
            Q(to_user=user) | Q(from_user=user)
        )

    def get(self, *args, **kwargs):
        from friendship.models import Friendship

        user_a, user_b = kwargs.get("user_a", None), kwargs.get("user_b", None)
        if user_a and user_b:
            try:
                return self.get(to_user=user_a, from_user=user_b)
            except Friendship.DoesNotExist:
                pass
            try:
                return self.get(to_user=user_b, from_user=user_a)
            except Friendship.DoesNotExist:
                return None
        return super().get(*args, **kwargs)

    def get_mutual_friends(self, user_a, user_b):
        output = []
        for friendship in user_a.friendship_set.all():
            friend = friendship.get_friend(user_a)
            if self.get(user_a=friend, user_b=user_b) and (friend != user_a and friend != user_b):
                output.append(friend)
        return output
