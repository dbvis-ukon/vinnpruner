import torchvision.datasets as datasets
import torchvision.transforms as T

def get_test_dataset(dataset, normalize=True, transform=False, resize=None):
	if dataset == 'mnist':
		transform_fun = None
		if transform:
			transform_fun = T.Compose([T.ToTensor(), T.Normalize((0.1307,), (0.3081,))]) if normalize else T.ToTensor()
		test_dataset = datasets.MNIST('./dataset/mnist', train=False, download=True, transform=transform_fun)

	elif dataset == 'cifar10':
		if resize != None:
			transform_fun = T.Compose([
				T.Resize(resize),
				T.ToTensor(),
				T.Normalize((0.4914, 0.4822, 0.4465), (0.247, 0.243, 0.261))],
			) if transform else None
		else:
			transform_fun = T.Compose([
				T.ToTensor(),
				T.Normalize((0.4914, 0.4822, 0.4465), (0.247, 0.243, 0.261))],
			) if transform else None
		test_dataset = datasets.CIFAR10('./dataset/cifar10', train=False, download=True, transform=transform_fun)

	return test_dataset

def get_dataset(dataset, normalize=True, resize=None):
	if dataset == 'mnist':
		transform = T.Compose([T.ToTensor(), T.Normalize((0.1307,), (0.3081,))]) if normalize else T.ToTensor()
		train_dataset = datasets.MNIST('./dataset/mnist', train=True, download=True, transform=transform)
		test_dataset = datasets.MNIST('./dataset/mnist', train=False, download=True, transform=transform)

	elif dataset == 'fmnist':
		transform = T.ToTensor()
		train_dataset = datasets.FashionMNIST('./dataset/fmnist', train=True, download=True, transform=transform)
		test_dataset = datasets.FashionMNIST('./dataset/fmnist', train=False, download=True, transform=transform)

	elif dataset == 'cifar10':
		if resize != None:
			transform_train = T.Compose([
				T.RandomCrop(32, padding=4),
				T.RandomHorizontalFlip(),
				T.Resize(resize),
				T.ToTensor(),
				T.Normalize((0.4914, 0.4822, 0.4465), (0.247, 0.243, 0.261))],
			)
			transform_test = T.Compose([
				T.ToTensor(),
				T.Resize(resize),
				T.Normalize((0.4914, 0.4822, 0.4465), (0.247, 0.243, 0.261))],
			)
		else:
			transform_train = T.Compose([
				T.RandomCrop(32, padding=4),
				T.RandomHorizontalFlip(),
				T.ToTensor(),
				T.Normalize((0.4914, 0.4822, 0.4465), (0.247, 0.243, 0.261))],
			)
			transform_test = T.Compose([
				T.ToTensor(),
				T.Normalize((0.4914, 0.4822, 0.4465), (0.247, 0.243, 0.261))],
			)
		train_dataset = datasets.CIFAR10('./dataset/cifar10', train=True, download=True, transform=transform_train)
		test_dataset = datasets.CIFAR10('./dataset/cifar10', train=False, download=True, transform=transform_test)

	elif dataset == 'tiny-imagenet':
		transform_train = T.Compose([
			T.RandomResizedCrop(64),
			T.RandomHorizontalFlip(),
			T.ToTensor(),
			T.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))],
		)
		transform_test = T.Compose([
			T.ToTensor(),
			T.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))],
		)
		train_dataset = datasets.ImageFolder('./data/tiny-imagenet-200/train', transform_train)
		test_dataset = datasets.ImageFolder('./data/tiny-imagenet-200/val', transform_test)

	else:
		raise ValueError('Unknown dataset')

	return train_dataset, test_dataset


