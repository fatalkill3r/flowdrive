def notifications(request):
    if not request.user.is_authenticated:return {}
    qs=request.user.notifications.all();return {"unread_notification_count":qs.filter(is_read=False).count(),"navbar_notifications":qs[:5]}
