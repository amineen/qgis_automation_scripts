def calculate_points_distance(totalDistance: float, min_distance=35, max_distance=55):

    if totalDistance < min_distance:
        # If totalDistance is less than min_distance,
        # you cannot place any point between
        return 0, totalDistance

    # Calculate the maximum number of intervals (of 55m) that fit in the total distance
    number_of_points = totalDistance // max_distance

    # Calculate the remaining distance after using number_of_points
    remaining_distance = totalDistance % max_distance

    if remaining_distance > 0:
        number_of_points += 1

    distance_between_points = totalDistance / number_of_points

    return number_of_points, distance_between_points
