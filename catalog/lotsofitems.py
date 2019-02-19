from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Categories, CategoryItem, User

# Create database and create a shortcut for easier to update database
engine = create_engine('sqlite:///moviecatalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create dummy user
User1 = User(name="Lavanya", email="164g1a0547@srit.ac.in")
session.add(User1)
session.commit()


# Create category of Adventure Films
category1 = Categories(name="Adventure Films", user_id=1)
session.add(category1)
session.commit()

# Create category of Comedy Films
category2 = Categories(user_id=1, name="Comedy Films")
session.add(category2)
session.commit()

# Create category of Horror Films
category3 = Categories(user_id=1, name="Horror Films")
session.add(category3)
session.commit()

# Create category of Musicals (Dance) Films
category4 = Categories(user_id=1, name="Musicals (Dance) Films")
session.add(category4)
session.commit()

# Add Items into categories
categoryItem1 = CategoryItem(user_id=1,
                             name="Pirates of the Caribbean: \
                             Dead Men Tell No Tales",
                             likes=698, dislikes=127, views=12467,
                             categories=category1,
                             img_url="https://images-na.ssl-images-amazon.com \
                             /images/I/51fX40gGdXL._SY445_.jpg")
session.add(categoryItem1)
session.commit()

categoryItem1 = CategoryItem(user_id=1,
                             name="sherlock Holmes",
                             likes=2014, dislikes=25, views=35410,
                             categories=category1,
                             img_url="https://images-na.ssl-images-amazon.com \
                             /images/I/A1AbomInUAL._RI_.jpg")
session.add(categoryItem1)
session.commit()
categoryItem1 = CategoryItem(user_id=1, name="Delhi Belly",
                             likes=547, dislikes=47, views=16547,
                             categories=category2,
                             img_url="https://img.nowrunning.com/content \
                             /movie/2011/DelhiBelly/bg13.jpg")
session.add(categoryItem1)
session.commit()

categoryItem1 = CategoryItem(user_id=1, name="Bad Neighbours 2",
                             likes=150, dislikes=47, views=1647,
                             categories=category2,
                             img_url="https://cdn-2.cinemaparadiso.co.uk \
                             /1609131015284_l.jpg")
session.add(categoryItem1)
session.commit()

categoryItem1 = CategoryItem(user_id=1, name="Evil dead 2",
                             likes=130, dislikes=123, views=135574,
                             categories=category3,
                             img_url="https://images-na.ssl-images-amazon.com \
                             /images/I/512jw2e5odL._SY445_.jpg")
session.add(categoryItem1)
session.commit()

categoryItem1 = CategoryItem(user_id=1, name="The Silence of the Lambs",
                             likes=500, dislikes=200, views=4565,
                             categories=category3,
                             img_url="https://images-na.ssl-images-amazon.com \
                             /images/I/51SHYSFNP2L._SY445_.jpg")
session.add(categoryItem1)
session.commit()

categoryItem1 = CategoryItem(user_id=1, name="sirivennela",
                             likes=413, dislikes=89, views=165058,
                             categories=category4,
                             img_url="https://a10.gaanacdn.com/images/albums \
                             /42/14442/crop_175x175_14442.jpg")
session.add(categoryItem1)
session.commit()


categoryItem1 = CategoryItem(user_id=1, name="Dance Academy: The Movie",
                             likes=300, dislikes=25, views=3686,
                             categories=category4,
                             img_url="https://i.ebayimg.com/images/g/-q0AA  \
                             OSwRLZab1wU/s-l300.jpg")
session.add(categoryItem1)
session.commit()
print "added category items!"
